Release Notes
=============

0.7
---

Data access
~~~~~~~~~~~

- A new :meth:`~.get_dask_array` method to access data as a Dask array
  (:ghpull:`212`). `Dask <https://docs.dask.org/en/latest/>`_ is a powerful tool
  for working with large amounts of data and doing computation in parallel.
- :func:`~.open_run` and :func:`~.RunDirectory` now take an optional
  ``include=`` glob pattern to select files to open (:ghpull:`221`).
  This can make opening a run faster if you only need to read certain files.
- Trying to open a run directory to which you don't have read access now
  correctly raises PermissionError (:ghpull:`210`).
- :func:`~.stack_detector_data` has a new parameter ``real_array``. Passing
  ``real_array=False`` avoids copying the data into a temporary array on the way
  to assembling images with detector geometry (:ghpull:`196`).
- When you open a run directory with :func:`~.open_run` or
  :func:`~.RunDirectory`, karabo_data tries to cache the metadata describing
  what data is in each file (:ghpull:`206`).
  Once the cache is created, opening the run again should be much faster,
  as it only needs to open the files containing the data you want.
  See :ref:`run-map-caching` for the details of how this works.
- Importing ``karabo_data`` is faster, as packages like xarray and pandas are
  now only loaded if you use the relevant methods (:ghpull:`207`).
- :ref:`cmd-lsxfel` and :meth:`~.DataCollection.info` are faster in some cases,
  as they only look in one file for the detector data shape (:ghpull:`219`).
- :meth:`~.DataCollection.get_array` is slightly faster, as it avoids copying
  data in memory unnecessarily (:ghpull:`209`)
- When you select sources with :meth:`~.DataCollection.select` or
  :meth:`~.DataCollection.deselect`, the resulting DataCollection no longer
  keeps references to files with no selected data. This should make it easier
  to then combine data with :meth:`~.DataCollection.union` in some situations
  (:ghpull:`202`).
- :doc:`Data validation <validation>` now checks that indexes have one entry per
  train ID.

Detector geometry
~~~~~~~~~~~~~~~~~

- :meth:`~.AGIPD_1MGeometry.plot_data_fast` is much more flexible, e.g.
  if you want to add a colorbar or draw the image as part of a larger figure
  (:ghpull:`205`). See its documentation for the new parameters.


0.6
---

Data access
~~~~~~~~~~~

- The :ref:`cmd-serve-files` command now takes ``--source`` and ``--key``
  options to select data to stream. They can be used with exact source names
  or with glob-style patterns, e.g. ``--source '*/DET/*'`` (:ghpull:`183`).
- Skip checking that ``.h5`` files in a run directory are HDF5 before trying to
  open them (:ghpull:`187`). The error is still handled if they are not.

Detector geometry
~~~~~~~~~~~~~~~~~

- Assembling detector data into images can now reuse an output array - see
  :meth:`~.AGIPD_1MGeometry.position_modules_fast` and
  :meth:`~.AGIPD_1MGeometry.output_array_for_position_fast` (:ghpull:`186`).
- CrystFEL format geometry files can now be written for 2D input arrays with the
  modules arranged along the slow-scan axis, as used by OnDA (:ghpull:`191`).
  To do this, pass ``dims=('frame', 'ss', 'fs')`` to
  :meth:`~.AGIPD_1MGeometry.write_crystfel_geom`.
- The geometry code has been reworked to use metres internally (:ghpull:`193`),
  along with other refactorings in :ghpull:`184` and :ghpull:`192`.
  These changes should not affect the public API.

0.5
---

Data access
~~~~~~~~~~~

- New method :meth:`~.get_data_counts` to find how many data points were
  recorded in each train for a given source and key.
- Create a virtual dataset for any single dataset with
  :meth:`~.get_virtual_dataset` (:ghpull:`162`).
  See :doc:`parallel_example` for how this can be useful.
- Write a file with virtual datasets for all selected data with
  :meth:`~.write_virtual` (:ghpull:`132`).
- Data from the supported multi-module detectors (AGIPD, LPD & DSSC) can be
  exposed in CXI format using a virtual dataset - see
  :meth:`~.write_virtual_cxi` (:ghpull:`150`, :ghpull:`166`, :ghpull:`173`).
- New class :class:`~.DSSC` for accessing DSSC data (:ghpull:`171`).
- New function :func:`~.open_run` to access a run by proposal and run number
  rather than path (:ghpull:`147`).
- :func:`~.stack_detector_data` now allows input data where some sources don't
  have the specified key (:ghpull:`141`).
- Files in the new ``1.0`` data format can now be opened (:ghpull:`182`).

Detector geometry
~~~~~~~~~~~~~~~~~

- New class :class:`~.DSSC_Geometry` for handling DSSC detector geometry (:ghpull:`155`).
- :class:`~.LPD_1MGeometry` can now read and write CrystFEL format
  geometry files, and produce PyFAI distortion arrays (:ghpull:`168`, :ghpull:`129`).
- :meth:`~.AGIPD_1MGeometry.write_crystfel_geom` (for AGIPD and LPD geometry)
  now accepts various optional parameters for other details to be written into
  the geometry file, such as the detector distance (``clen``) and the photon
  energy (:ghpull:`168`).
- New method :meth:`~.AGIPD_1MGeometry.get_pixel_positions` to get the physical
  position of every pixel in a detector, for all of AGIPD, LPD and DSSC
  (:ghpull:`142`).
- New method :meth:`~.AGIPD_1MGeometry.data_coords_to_positions` to convert data
  array coordinates to physical positions, for AGIPD and LPD (:ghpull:`142`).

0.4
---

- Python 3.5 is now the minimum required version.
- Fix compatibility with numpy 1.14 (the version installed in Anaconda on the
  Maxwell cluster).
- Better error message from :func:`~.stack_detector_data` when passed
  non-detector data.

0.3
---

New features:

- New interfaces for working with :doc:`geometry`.
- New interfaces for accessing :doc:`agipd_lpd_data`.
- :meth:`~.DataCollection.select_trains` can now select arbitrary specified
  trains, not just a slice.
- :meth:`~.DataCollection.get_array` can take a region of interest (``roi``)
  parameter to select a slice of data from each train.
- A newly public :meth:`~.DataCollection.keys_for_source` method to list keys
  for a given source.

Fixes:

- :func:`~.stack_detector_data` can handle missing detector modules.
- Source sets have been changed to frozen sets. Use
  :meth:`~.DataCollection.select` to choose a subset of sources.
- :meth:`~.DataCollection.get_array` now only loads the data for selected
  trains.
- :meth:`~.DataCollection.get_array` works with data recorded more than once per
  train.

0.2
---

- New command ``karabo-data-validate`` to check the integrity of data files.
- New methods to select a subset of data: :meth:`~.DataCollection.select`,
  :meth:`~.DataCollection.deselect`, :meth:`~.DataCollection.select_trains`,
  :meth:`~.DataCollection.union`,
- Selected data can be written back to a new HDF5 file with
  :meth:`~.DataCollection.write`.
- :func:`~.RunDirectory` and :func:`~.H5File` are now functions which return a
  :class:`DataCollection` object, rather than separate classes. Most code using
  these should still work, but checking the type with e.g. ``isinstance()``
  may break.
