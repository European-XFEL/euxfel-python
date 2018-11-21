from copy import copy
import h5py
from itertools import product
import numpy as np
import sys
from textwrap import indent

def splitChannelDataIntoTiles(channelData, clockwiseOrder=False):
    """Splits the raw channel data into indiviual tiles

    Args
    ----

    channelData : ndarray
        Raw channel data. Must have shape (256, 256)

    clockwiseOrder : bool, optional
        If set to True, the sequence of tiles is given
        in the clockwise order starting with the top
        right tile (LPD standard). If set to false, tile
        data is returned in reading order

    Returns
    -------

    ndarray
        Same data, but reshaped into (12, 32, 128)
    """
    extra_dims = channelData.shape[:-2]
    a = np.asarray(np.split(channelData, 8, axis=-2))
    a = np.asarray(np.split(a, 2, axis=-1))
    a = np.reshape(a, (16,) + extra_dims + (32, 128))
    orderedTiles = a

    if clockwiseOrder:
        # The official LPD tile order is clockwise from the top right tile.
        # We need them in this order to apply the right offset to the right tile.
        readingOrderToClockwise = list(range(7, -1, -1)) + list(range(8, 16))
        orderedTiles = orderedTiles[readingOrderToClockwise]
    return orderedTiles


class GeometryFragment:
    def __init__(self, offset, children):
        self.offset = offset  # in m
        self.children = children

    def _str_lines(self):
        r = []
        for name, child in sorted(self.children.items()):
            r.append("{}: {}".format(name, child.offset))
            r.extend(indent(str(child), '  ').splitlines())
        return r

    def __str__(self):
        return '\n'.join(self._str_lines())

    def find_offset(self, name_parts):
        if name_parts:
            child = self.children[name_parts[0]]
            return self.offset + child.find_offset(name_parts[1:])
        return self.offset

    def iter_leaf_paths(self):
        if not self.children:
            yield ()
            return
        for k, v in sorted(self.children.items()):
            for subpath in v.iter_leaf_paths():
                yield (k,) + subpath

    @classmethod
    def from_h5_group(cls, group, unit=1e-3):
        children = {key: GeometryFragment.from_h5_group(val)
                    for (key, val) in group.items()
                    if isinstance(val, h5py.Group)
                   }
        return cls(group['Position'][:] * unit, children)

class LPDGeometry(GeometryFragment):
    pixel_size = 0.5e-3  # Meter: 0.5 Millimeter

    @classmethod
    def from_h5_file_and_quad_positions(cls, file, positions, unit=1e-3):
        children = {}
        for n, position in enumerate(positions, start=1):
            quad = 'Q%d' % n
            modules = {name: GeometryFragment.from_h5_group(group, unit=unit)
                       for (name, group) in file[quad].items()}
            children[quad] = GeometryFragment(np.asarray(position) * unit, modules)

        return cls(np.asarray((0, 0)), children)

    def position_all_modules(self, data):
        """Assemble data from this detector according to where the pixels are.

        Parameters
        ----------

        data : ndarray
          The last three dimensions should be channelno, pixel_y, pixel_x
          (lengths 16, 256, 256).
          Other dimensions before these will be preserved in the output.

        Returns
        -------
        out : ndarray
          Array with the one dimension fewer than the input.
          The last two dimensions represent pixel y and x in the detector space.
        centre : ndarray
          (x, y) pixel location of the detector centre in this geometry.
        """
        assert data.shape[-3:] == (16, 256, 256)
        size_xy, centre = self._plotting_dimensions()
        size_yx = size_xy[::-1]
        out = np.empty(data.shape[:-3] + size_yx,
                       dtype=data.dtype)
        out[:] = np.nan

        for channelno in range(16):
            module_data = data[..., channelno, :, :]

            Q = 'Q{:d}'.format(channelno // 4 + 1)
            M = 'M{:d}'.format(channelno % 4 + 1)
            module_tiles_data = splitChannelDataIntoTiles(module_data, clockwiseOrder=True)
            for tileno, tile_data in enumerate(module_tiles_data, start=1):
                T = "T{:02d}".format(tileno)
                position = self.find_offset((Q, M, T))
                # Convert physical position (m) to pixel location:
                x0, y0 = (position // self.pixel_size) + centre
                x0, y0 = int(x0), int(y0)

                out[..., y0:y0 + tile_data.shape[-2],
                         x0:x0 + tile_data.shape[-1]] = tile_data[..., ::-1, ::-1]

        return out, centre

    def _plotting_dimensions(self):
        """Calculate appropriate dimensions for plotting assembled data

        Returns (size_x, size_y), (centre_x, centre_y)
        """
        min_x = max_x = min_y = max_y = 0
        for path in self.iter_leaf_paths():
            x, y = self.find_offset(path)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        # Convert physical distances to pixels
        # Add 20px margin, plus the 128*32 tile size
        min_x = int(min_x // self.pixel_size) - 20
        max_x = int(max_x // self.pixel_size) + 128 + 20
        min_y = int(min_y // self.pixel_size) - 20
        max_y = int(max_y // self.pixel_size) + 32 + 20

        size = (max_x - min_x), (max_y - min_y)
        centre = np.asarray([-min_x, -min_y])
        return size, centre

    def plot_data(self, modules_data):
        """Plot data from the detector using this geometry.

        Returns a matplotlib figure.

        Parameters
        ----------

        modules_data : ndarray
          Should have exactly 3 dimensions: channelno, pixel_y, pixel_x
          (lengths 16, 256, 256).
        """
        from matplotlib.cm import viridis
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        fig = Figure((10, 10))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)
        my_viridis = copy(viridis)
        # Use a dark grey for missing data
        my_viridis.set_bad('0.25', 1.)

        res, centre = self.position_all_modules(modules_data)
        ax.imshow(res, cmap=my_viridis)

        cx, cy = centre
        ax.hlines(cy, cx - 20, cx + 20, colors='w', linewidths=1)
        ax.vlines(cx, cy - 20, cy + 20, colors='w', linewidths=1)
        return fig

    def inspect(self):
        """Plot the 2D layout of this detector geometry.

        Returns a matplotlib Figure object.
        """
        # from matplotlib.backends.backend_agg import FigureCanvasAgg
        # from matplotlib.figure import Figure

        fig = Figure((10, 10))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)

        size_xy, centre = self._plotting_dimensions()
        size_yx = size_xy[::-1]  # Our array indexing is [y, x]
        bg = np.ones(size_yx + (3,), dtype='f4')

        # Mark the centre location
        cx, cy = centre
        ax.hlines(cy, cx - 100, cx + 100, colors='0.75', linewidths=2)
        ax.vlines(cx, cy - 100, cy + 100, colors='0.75', linewidths=2)

        # Show where detector elements (modules & tiles) are positioned.
        for (Q, M) in product(range(1, 5), range(1, 5)):
            position = self.find_offset(('Q%d' % Q, 'M%d' % M))
            xm, ym = (position // self.pixel_size) + centre
            ax.text(xm, ym, 'Q%dM%d' % (Q, M), color='k', ha='left', va='top',
                    bbox={'facecolor': 'w'})
            for T in range(1, 17):
                position = self.find_offset(('Q%d' % Q, 'M%d' % M, 'T%02d' % T))
                xt, yt = (position // self.pixel_size) + centre
                xt, yt = int(xt), int(yt)
                # Draw a light green block for each tile
                bg[yt:yt + 32, xt:xt + 128] = (0.75, 1.0, 0.75)
                # Label specific tiles to show the ordering
                if T in [1, 8, 9]:
                    ax.text(xt, yt, str(T), va='top', ha='left')

        ax.imshow(bg, origin='upper')
        ax.set_title('LPD detector geometry')
        return fig

    def generateDistortion(self):
        """ Return distortion matrix for LPD detector

        Returns
        -------
        out: ndarray
            Dimension (Ny=1024, Nx=1024, 4, 3)
            type: float32
            4 is the number of corners of a pixel
            last dimension is for Z, Y, X location of each corner
        """
        _quad, _modules, _tiles = self._create_qmt_dict()
        _, centre = self._plotting_dimensions()
        distortion = np.zeros((1024, 1024, 4, 3), dtype=np.float32)

        for (Q, M) in product(range(1, 5), range(1, 5)):

            for T in range(1, 17):
                position = self.find_offset(('Q%d' % Q,
                                             'M%d' % M, 'T%02d' % T))

                # idx, idy : Bottom left index of tiles in (1024,1024) array
                idx, idy = np.add(_quad['Q%d' % Q],
                                  np.add(_modules['M%d' % M],
                                  _tiles['T%01d' % T]))

                xt, yt = (position // self.pixel_size) + centre
                xt, yt = int(xt), int(yt)
                # y_position contains y_indices of pixels for a tile
                y_position = np.array(
                    [yt+j for j, _ in product(range(32), range(128))]).\
                    reshape(32, 128)
                # x_position contains x_indices of pixels for a tile
                x_position = np.array(
                    [xt+i for _, i in product(range(32), range(128))]).\
                    reshape(32, 128)
                # From the pixel location evaluate X and Y corordinates
                # of its 4 corners in real space.
                # Z position is set to 0 (Flat detector)
                distortion[idy:idy+32, idx:idx+128, 0, 1] = (
                    self.pixel_size*y_position[:, :] - 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 1, 1] = (
                    self.pixel_size*y_position[:, :] + 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 2, 1] = (
                    self.pixel_size*y_position[:, :] + 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 3, 1] = (
                    self.pixel_size*y_position[:, :] - 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 0, 2] = (
                    self.pixel_size*x_position[:, :] - 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 1, 2] = (
                    self.pixel_size*x_position[:, :] - 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 2, 2] = (
                    self.pixel_size*x_position[:, :] + 0.5*self.pixel_size)
                distortion[idy:idy+32, idx:idx+128, 3, 2] = (
                    self.pixel_size*x_position[:, :] + 0.5*self.pixel_size)

        return distortion

    def _create_qmt_dict(self):
        """Returns dictionaries for bottom left indices

        _quad : bottom left index of all 4 quadrants in 1024,1024 canvas
        _modules: botton left index of 4 modules with respect to quadrant
        _tiles: bottom left index of 16 tiles with respect to the module
        """
        _quad, _modules, _tiles = dict(), dict(), dict()

        # Bottom left position index of Quadrants Size (1024,1024)
        # See locations from inspect()
        _quad['Q1'] = (512, 0)
        _quad['Q2'] = (512, 512)
        _quad['Q3'] = (0, 512)
        _quad['Q4'] = (0, 0)

        # Bottom left position index of modules with respect to Quadrant
        _modules['M1'] = (256, 0)
        _modules['M2'] = (256, 256)
        _modules['M3'] = (0, 256)
        _modules['M4'] = (0, 0)

        # Bottom left position index of tiles with respect to Modules
        offset_r = (128, 0)
        offset_l = (0, 256)
        for tileno in range(1,17):
            if tileno <= 8:
                _tiles['T%d' % tileno] = tuple(offset_r)
                offset_r = np.add(offset_r, (0, 32))
            else:
                offset_l = np.subtract(offset_l, (0, 32))
                _tiles['T%d' % tileno] = tuple(offset_l)

        return _quad, _modules, _tiles


if __name__ == '__main__':

    quadpos = [(-11.4, -299), (11.5, -8), (-254.5, 16), (-278.5, -275)]  # MAR 18
    with h5py.File(sys.argv[1], 'r') as f:
        geom = LPDGeometry.from_h5_file_and_quad_positions(f, quadpos, unit=1e-3)

    print(geom)
    print('Q2/M1/T07:', geom.find_offset(('Q2', 'M1', 'T07')))

