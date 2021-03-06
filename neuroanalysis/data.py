"""
Data Abstraction Layer
----------------------

These classes present a high-level API for handling data from various types of neurophysiology experiments.
They do not implement functionality for reading any particular type of data file, though. Rather, they
provide an abstraction layer that separates analysis and visualization from the idiosyncratic
details of any particular data acquisition system.

Each data acquisition system can provide a set of subclasses to adapt its data formats to this API
(as long as the data are reasonably similar), and analysis tools should rely only on this API to ensure
that they will not need to be rewritten in order to support data collected under different acquisition
systems.

This abstraction layer also helps to enforce good coding practice by separating data representation,
analysis, and visualization.
"""
from __future__ import division

import numpy as np
import scipy.signal
from . import util
from collections import OrderedDict
from .stats import ragged_mean
from .baseline import float_mode


class Container(object):
    """Generic hierarchical container. 
    
    This class is the basis for most other classes in the DAL.
    """
    def __init__(self):
        self._meta = OrderedDict()
        
    @property
    def parent(self):
        return None
    
    @property
    def children(self):
        return []

    @property
    def key(self):
        """Key that uniquely identifies this object among its siblings.
        """
        return None
    
    @property
    def meta(self):
        return self._meta

    @property
    def all_children(self):
        allch = [self]
        for ch in self.children:
            allch.extend(ch.all_children)
        return allch

    @property
    def all_meta(self):
        allmeta = OrderedDict()
        for obj in self.path:
            m = obj.meta
            allmeta.update(m)
        return allmeta
        
    @property
    def path(self):
        obj = self
        path = []
        while obj is not None:
            path.append(obj)
            obj = obj.parent
        return path[::-1]


class Experiment(Container):
    """A generic container for RecordingSequence and SyncRecording instances that
    were acquired together.
    
    The boundaries between one experiment and the next are sometimes ambiguous, but
    in general we group multiple recordings into an experiment if they are likely to
    be analyzed together. Likewise, recordings that have no causal relationship
    to each other probably belong in different Experiment containers. For example,
    a series of recordings made on the same cell almost certainly belong in the same
    Experiment, whereas recordings made from different pieces of tissue probably
    belong in different Experiments.
    """
    def __init__(self, data=None, meta=None):
        Container.__init__(self)
        self._data = data
        if meta is not None:
            self._meta.update(OrderedDict(meta))
    
    @property
    def contents(self):
        """A list of data objects (Trace, Recording, SyncRecording, RecordingSequence)
        directly contained in this experiment.
        
        Grandchild objects are not included in this list.
        """
        return self._data[:]

    def find(self, type):
        return [c for c in self.all_children if isinstance(c, type)]

    @property
    def all_traces(self):
        return self.find(Trace)
    
    @property
    def all_recordings(self):
        return self.find(Recording)

    @property
    def all_sync_recordings(self):
        return self.find(SyncRecording)

    def meta_table(self, objs):
        # collect all metadata
        meta = []
        for i,o in enumerate(objs):
            meta.append(o.all_meta)
            
        # generate a list of common fields (in the correct order)
        fields = set(meta[0].keys())
        for m in meta[1:]:
            fields &= set(m.keys())
        order = list(meta[0].keys())
        for k in order[:]:
            if k not in fields:
                order.remove(k)
        
        # transpose
        tr = OrderedDict()
        for k in order:
            tr[k] = [m[k] for m in meta]
        
        # create a table
        import pandas
        return pandas.DataFrame(tr)

    @property
    def trace_table(self):
        return self.meta_table(self.all_traces)

    @property
    def parent(self):
        """None
        
        This is a convenience property used for traversing the object hierarchy.
        """
        return None
    
    @property
    def children(self):
        """Alias for self.contents
        
        This is a convenience property used for traversing the object hierarchy.
        """
        return self.contents
    
    

class RecordingSequence(Container):
    
    #  Acquisition?
    #  RecordingSet?
    
    #  Do we need both SyncRecordingSequence and RecordingSequence ?
    #  Can multiple RecordingSequence instances refer to the same underlying sequence?
    #    - Let's say no--otherwise we have to worry about unique identification, comparison, etc.
    #    - Add ___View classes that slice/dice any way we like.
    
    """Representation of a sequence of data acquisitions.

    For example, this could be a single type of acquisition that was repeated ten times,
    or a series of ten acquisitions that varies one parameter across ten values.
    Usually the recordings in a sequence all use the same set of devices.

    Sequences may be multi-dimensional and may vary more than one parameter.
    
    Items in a sequence are usually SyncRecording instances, but may also be
    nested RecordingSequence instances.
    """
    @property
    def type(self):
        """An arbitrary string representing the type of acquisition.
        """
        pass

    @property
    def shape(self):
        """The array-shape of the sequence.
        """

    @property
    def ndim(self):
        return len(self.shape)

    def __getitem__(self, item):
        """Return one item (a SyncRecording instance) from the sequence.
        """

    def sequence_params(self):
        """Return a structure that describes the parameters that are varied across each
        axis of the sequence.

        For example, a two-dimensional sequence might return the following:

            [
                [param1, param2],   # two parameters that vary across the first sequence axis
                [],  # no parameters vary across the second axis (just repetitions)
                [param3],  # one parameter that varies across all recordings, regardless of its position along any axis
            ]

        Each parameter must be a key in the metadata for a single recording.
        """

    @property
    def parent(self):
        """None
        
        This is a convenience property used for traversing the object hierarchy.
        """
        return None
    
    @property
    def children(self):
        """Alias for self.contents
        
        This is a convenience property used for traversing the object hierarchy.
        """
        return self.contents


class IVCurve(RecordingSequence):
    """A sequence of recordings on a single patch-clamp amplifier that vary the amplitude
    of a current or voltage pulse, typically used to characterize intrinsic membrane properties
    of the cell.
    """


class SyncRecording(Container):
    """Representation of multiple synchronized recordings.

    This is typically the result of recording from multiple devices at the same time
    (for example, two patch-clamp amplifiers and a camera).
    """
    def __init__(self, recordings=None, parent=None):
        self._parent = parent
        self._recordings = recordings if recordings is not None else OrderedDict()
        Container.__init__(self)

    @property
    def type(self):
        """An arbitrary string representing the type of acquisition.
        """
        pass

    @property
    def devices(self):
        """A list of the names of devices in this recording.
        """
        return self._recordings.keys()

    def __getitem__(self, item):
        """Return a recording given its device name.
        """
        return self._recordings[item]

    @property
    def recordings(self):
        """A list of the recordings in this syncrecording.
        """
        return self._recordings.values()

    def data(self):
        return np.concatenate([self[dev].data()[None, :] for dev in self.devices], axis=0)

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self.recordings


device_tree = {
    'patch clamp amplifier': {
        'MultiClamp 700': [
            'MultiClamp 700A',
            'MultiClamp 700B',
        ],
    },
}


class Recording(Container):
    """Representation of a single continuous data acquisition from a single device,
    possibly with multiple channels of data (for example, a recording from a single
    patch-clamp headstage with input and output channels, or ).
    
    Each channel is described by a single Trace instance. Channels are often 
    recorded with the same timebase, but this is not strictly required.
    """
    def __init__(self, channels=None, start_time=None, device_type=None, device_id=None, sync_recording=None):
        Container.__init__(self)
        self._meta = OrderedDict([
            ('start_time', start_time),
            ('device_type', device_type),
            ('device_id', device_id),
        ])
        
        if channels is None:
            channels = OrderedDict()
        else:
            channels = OrderedDict(channels)
            for k,v in channels.items():
                assert isinstance(v, Trace)
        self._channels = channels

        self._sync_recording = sync_recording
        
    @property
    def device_type(self):
        """A string representing the type of device that generated this recording.

        Strings should be described in the global ``device_tree``.        
        """
        return self._meta['device_type']

    @property
    def channels(self):
        """A list of channels included in this recording.
        """
        return self._channels.keys()

    @property
    def start_time(self):
        """The starting time (unix epoch) of this recording.
        """
        return self._meta['start_time']

    @property
    def device_id(self):
        return self._meta['device_id']
    
    @property
    def sync_recording(self):
        return self._sync_recording

    def __getitem__(self, chan):
        if isinstance(chan, slice):
            return RecordingView(self, chan)
        else:
            return self._channels[chan]

    def data(self):
        return np.concatenate([self[ch].data[:,None] for ch in self.channels], axis=1)

    @property
    def parent(self):
        return self.sync_recording
    
    @property
    def children(self):
        return [self[k] for k in self.channels]


class RecordingView(Recording):
    """A time-slice of a multi channel recording
    """
    def __init__(self, rec, sl):
        self._parent_rec = rec
        self._view_slice = sl
        chans = OrderedDict([(k, rec[k]) for k in rec.channels])
        Recording.__init__(self, 
            channels=chans, start_time=rec.start_time, device_type=rec.device_type,
            device_id=rec.device_id, sync_recording=rec.sync_recording)

    def __getattr__(self, attr):
        return getattr(self._parent_rec, attr)

    def __getitem__(self, item):
        return self._parent_rec[item][self._view_slice]

    @property
    def parent(self):
        return self._parent_rec

    @property
    def source_indices(self):
        """Return the indices of this view on the original Recording.
        """
        v = self
        start = 0
        while True:
            start += self._view_slice.start
            v = v.parent
            if not isinstance(v, RecordingView):
                break
        return start, start + len(self)


class PatchClampRecording(Recording):
    """Recording from a patch-clamp amplifier.

    * Current- or voltage-clamp mode
    * Minimum one recorded channel ('primary'), possibly more
    * Includes stimulus waveform ('command')
    * Metadata about amplifier state:
        * clamp_mode ('ic' 'i0', or 'vc')
        * holding potential (vc only)
        * holding_current (ic only)
        * bridge_balance (ic only)
        * lpf_cutoff
        * pipette_offset
    
    Should have at least 'primary' and 'command' channels.

    Note: command channel values should _include_ holding potential/current!
    """
    def __init__(self, *args, **kwds):
        meta = OrderedDict()
        extra_meta = ['cell_id', 'clamp_mode', 'patch_mode', 'holding_potential', 'holding_current',
                      'bridge_balance', 'lpf_cutoff', 'pipette_offset', 'baseline_potential',
                      'baseline_current', 'baseline_rms_noise', 'stim_name']
        for k in extra_meta:
            meta[k] = kwds.pop(k, None)
        self._baseline_data = None
        Recording.__init__(self, *args, **kwds)
        self._meta.update(meta)
        
    @property
    def cell_id(self):
        """Uniquely identifies the cell attached in this recording.
        """
        return self._meta['cell_id']
        
    @property
    def clamp_mode(self):
        """The mode of the patch clamp amplifier: 'vc', 'ic', or 'i0'.
        """
        return self._meta['clamp_mode']

    @property
    def patch_mode(self):
        """The state of the membrane patch. E.g. 'whole cell', 'cell attached', 'loose seal', 'bath', 'inside out', 'outside out'
        """
        return self._meta['patch_mode']

    @property
    def holding_potential(self):
        """The command holding potential if the recording is voltage-clamp, or the
        resting membrane potential if the recording is current-clamp.
        """
        if self.clamp_mode == 'vc':
            return self._meta['holding_potential']
        else:
            return self.baseline_potential
            
    @property        
    def rounded_holding_potential(self, increment=5e-3):
        """Return the holding potential rounded to the nearest increment.
        
        The default increment rounds to the nearest 5 mV.
        """
        hp = self.holding_potential
        if hp is None:
            return None
        return increment * np.round(hp / increment)

    @property
    def holding_current(self):
        """The steady-state pipette current applied during this recording.
        """
        if self.clamp_mode == 'ic':
            return self._meta['holding_current']
        else:
            return self.baseline_current

    @property
    def nearest_test_pulse(self):
        """The test pulse that was acquired nearest to this recording.
        """

    @property
    def baseline_regions(self):
        """A list of (start,stop) index pairs that cover regions of the recording
        the cell is expected to be in a steady state.
        """
        return []

    @property
    def baseline_data(self):
        """All items in baseline_regions concatentated into a single trace.
        """
        if self._baseline_data is None:
            data = [self['primary'].data[start:stop] for start,stop in self.baseline_regions]
            if len(data) == 0:
                data = np.empty(0, dtype=self['primary'].data.dtype)
            else:
                data = np.concatenate(data)
            self._baseline_data = Trace(data, sample_rate=self['primary'].sample_rate, recording=self)
        return self._baseline_data

    @property
    def baseline_potential(self):
        """The mode potential value from all quiescent regions in the recording.

        See float_mode()
        """
        if self.meta['baseline_potential'] is None:
            if self.clamp_mode == 'vc':
                self.meta['baseline_potential'] = self.meta['holding_potential']
            else:
                data = self.baseline_data.data
                if len(data) == 0:
                    return None
                self.meta['baseline_potential'] = float_mode(data)
        return self.meta['baseline_potential']

    @property
    def baseline_current(self):
        """The mode current value from all quiescent regions in the recording.

        See float_mode()
        """
        if self.meta['baseline_current'] is None:
            if self.clamp_mode == 'ic':
                self.meta['baseline_current'] = self.meta['holding_current']
            else:
                data = self.baseline_data.data
                if len(data) == 0:
                    return None
                self.meta['baseline_current'] = float_mode(data)
        return self.meta['baseline_current']

    @property
    def baseline_rms_noise(self):
        """The standard deviation of all data from quiescent regions in the recording.
        """
        if self.meta['baseline_rms_noise'] is None:
            data = self.baseline_data.data
            if len(data) == 0:
                return None
            self.meta['baseline_rms_noise'] = data.std()
        return self.meta['baseline_rms_noise']

    def _descr(self):
        mode = self.clamp_mode
        if mode == 'vc':
            hp = self.holding_potential
            if hp is not None:
                hp = int(np.round(hp*1e3))
            extra = "mode=VC holding=%s" % hp
        elif mode == 'ic':
            hc = self.holding_current
            if hc is not None:
                hc = int(np.round(hc*1e12))
            extra = "mode=IC holding=%s" % hc

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self._descr())


class Trace(Container):
    """A homogeneous time series data set. 
    
    This is a representation of a single stream of data recorded over time. The
    data must be representable as a single N-dimensional array where the first
    array axis is time. 
    
    Examples:
    
    * A membrane potential recording from a single current-clamp headstage
    * A video stream from a camera
    * A digital trigger waveform
    
    Traces may specify units, a starting time, and either a sample period or an
    array of time values.
    """
    def __init__(self, data=None, dt=None, t0=None, sample_rate=None, start_time=None, time_values=None, units=None, channel_id=None, recording=None, **meta):
        Container.__init__(self)
        
        if data is not None and data.ndim != 1:
            raise ValueError("data must be a 1-dimensional array.")
        
        if time_values is not None:
            if data is not None and time_values.shape != data.shape:
                raise ValueError("time_values must have the same shape as data.")
            if dt is not None:
                raise TypeError("Cannot specify both time_values and dt.")
            if sample_rate is not None:
                raise TypeError("Cannot specify both time_values and sample_rate.")
            if t0 is not None:
                raise TypeError("Cannot specify both time_values and t0.")

        if dt is not None and sample_rate is not None:
            raise TypeError("Cannot specify both sample_rate and dt.")
            
        self._data = data
        self._meta = OrderedDict([
            ('start_time', start_time),
            ('dt', dt),
            ('t0', t0),
            ('sample_rate', sample_rate),
            ('units', units),
            ('channel_id', channel_id),
        ])
        self._meta.update(meta)
        self._time_values = time_values
        self._generated_time_values = None
        self._recording = recording
        
    @property
    def data(self):
        """The array of sample values.
        """
        return self._data
        
    @property
    def start_time(self):
        """The clock time (seconds since epoch) corresponding to the sample
        where t=0. 
        
        If self.t0 is equal to 0, then start_time is the clock time of the
        first sample.
        """
        return self._meta['start_time']
    
    @property
    def sample_rate(self):
        """The sample rate for this Trace.
        
        If no sample rate was specified, then this value is calculated from
        self.dt.
        """
        rate = self._meta['sample_rate']
        if rate is not None:
            return rate
        else:
            return 1.0 / self.dt

    @property
    def dt(self):
        """The time step between samples for this Trace.
        
        If no time step was specified, then this value is calculated from
        self.sample_rate.
        
        If both dt and sample_rate were not specified, then this value
        is calculated as the difference between the first two items in
        time_values.
        
        If no timing information was specified at all, then accessing this
        property raises TypeError.
        """
        # need to be very careful about how we calculate dt and sample rate
        # to avoid fp errors.
        dt = self._meta['dt']
        if dt is not None:
            return dt
        
        rate = self._meta['sample_rate']
        if rate is not None:
            return 1.0 / rate
        
        t = self.time_values
        if t is not None:
            # assume regular sampling.
            # don't cache this value; we want to remember whether the user 
            # provided dt or samplerate
            return t[1] - t[0]
        
        raise TypeError("No sample timing is specified for this trace.")

    @property
    def t0(self):
        """The value of the first item in time_values.
        
        Setting this property causes the entire array of time values to shift.
        """
        t0 = self._meta['t0']
        if t0 is not None:
            return t0
        if self._time_values is not None:
            return self._time_values[0]
        return 0
    
    @t0.setter
    def t0(self, t0):
        if self._time_values is not None and self._time_values[0] != t0:
            self._time_values = self._time_values + (t0 - self._time_values[0])
        else:
            self._meta['t0'] = t0
            self._generated_time_values = None

    @property
    def time_values(self):
        """An array of sample time values.
        
        Time values are specified in seconds relative to start_time.
        
        If no sample time values were provided for this Trace, then the array
        is automatically generated based on other timing metadata (t0, dt,
        sample_rate).
        
        If no timing information at all was specified for this Trace, then
        accessing this property raises TypeError.
        """
        if self._time_values is not None:
            return self._time_values
        
        if self._generated_time_values is None:
            dt = self._meta['dt']
            rate = self._meta['sample_rate']
            if dt is not None:
                self._generated_time_values = self.t0 + np.arange(len(self.data)) * dt
            elif rate is not None:
                self._generated_time_values = self.t0 + np.arange(len(self.data)) * (1.0 / rate)
            else:
                raise TypeError("No sample timing is specified for this trace.")
        
        return self._generated_time_values

    @property
    def regularly_sampled(self):
        """Boolean indicating whether the samples in this Trace have equal
        time intervals.
        
        If either dt or sample_rate was specified for this trace, then this
        property is True. If only time values were given, then this property
        is True if the intervals between samples differ by less than 1%.
        
        If no sample timing was specified for this Trace, then this property
        is False.
        """
        if not self.has_timing:
            return False
        
        if not self.has_time_values:
            return True
        
        tvals = self.time_values
        dt = np.diff(tvals)
        return np.all(dt - dt[0] < dt.mean() * 0.01)

    @property
    def has_timing(self):
        """Boolean indicating whether any timing information was specified for
        this Trace.
        """
        return (self.has_time_values or 
                self._meta['dt'] is not None or 
                self._meta['sample_rate'] is not None)

    @property
    def has_time_values(self):
        """Boolean indicating whether an array of time values was explicitly
        specified for this Trace.
        """
        return self._time_values is not None

    @property
    def units(self):
        return self._meta['units']

    @property
    def shape(self):
        return self.data.shape
    
    def __len__(self):
        return self.shape[0]
    
    @property
    def duration(self):
        if self.has_time_values:
            return self.time_values[-1] - self.t0
        else:
            return self.shape[0] * self.dt

    @property
    def ndim(self):
        return self.data.ndim
    
    @property
    def channel_id(self):
        return self._meta['channel_id']
    
    @property
    def recording(self):
        return self._recording

    def copy(self, data=None, time_values=None, **kwds):
        """Return a copy of this Trace.
        
        The new Trace will have the same data, timing information, and metadata
        unless otherwise specified in the arguments.
        
        Parameters
        ----------
        data : array | None
            If specified, sets the data array for the new Trace.
        time_values : array | None
            If specified, sets the time_values array for the new Trace.
        kwds :
            All extra keyword arguments will overwrite metadata properties.
            These include dt, sample_rate, t0, start_time, units, and
            others.
        """
        if data is None:
            data = self.data.copy()
        
        if time_values is None:
            tval = self._time_values
            if tval is not None:
                tval = tval.copy()
        else:
            tval = time_values
        
        meta = self._meta.copy()
        meta.update(kwds)
        
        return Trace(data, time_values=tval, recording=self.recording, **meta)

    @property
    def parent(self):
        return self.recording

    def __getitem__(self, item):
        if isinstance(item, slice):
            return TraceView(self, item)
        else:
            raise TypeError("Invalid Trace slice: %r" % item)

    def downsample(self, n=None, f=None):
        """Return a downsampled copy of this trace.
        
        Parameters
        ----------
        n : int
            (optional) number of samples to average
        f : float
            (optional) desired target sample rate
        """
        if not self.regularly_sampled:
            raise TypeError("downsample requires regularly-sampled data.")
        
        # choose downsampling factor
        if None not in (f, n):
            raise TypeError("Must specify either n or f (not both).")
        if n is None:
            if f is None:
                raise TypeError("Must specify either n or f.")
            n = int(np.round(self.sample_rate / f))
            if abs(n - (self.sample_rate / f)) > 1e-6:
                raise ValueError("Cannot downsample to %gHz; the resulting downsample factor is not an integer (try Trace.resample instead)." % f)
        if n == 1:
            return self
        if n <= 0:
            raise Exception("Invalid downsampling factor: %d" % n)
        
        # downsample
        data = util.downsample(self.data, n, axis=0)
        
        # handle timing
        tvals = self._time_values
        if tvals is not None:
            tvals = tvals[::n]
        dt = self._meta['dt']
        if dt is not None:
            dt = dt * n
        sr = self._meta['sample_rate']
        if sr is not None:
            sr = float(sr) / n
        
        return self.copy(data=data, time_values=tvals, dt=dt, sample_rate=sr)

    def resample(self, sample_rate):
        """Return a resampled copy of this trace.
        
        Parameters
        ----------
        sample_rate : float
            The new sample rate of the returned Trace

        Notes
        -----
        Lowpass filter followed by linear interpolation to extract new samples.

        Uses a bessel filter to avoid ringing artifacts, with cutoff=sample_rate
        and order=2 chosen to yield decent antialiasing and minimal blurring.

        scipy.resample was avoided due to ringing and edge artifacts.
        """
        if self.sample_rate == sample_rate:
            return self
        if not self.regularly_sampled:
            raise TypeError("resample requires regularly-sampled data.")
        
        ns = int(np.round(len(self) * sample_rate / self.sample_rate))

        # scipy.resample causes ringing and edge artifacts (freq-domain windowing
        # did not seem to help)
        # data = scipy.signal.resample(self.data, ns)

        # bessel filter gives reasonably good antialiasing with no ringing or edge
        # artifacts
        from .filter import bessel_filter
        filt = bessel_filter(self, cutoff=sample_rate, order=2)
        t1 = self.time_values
        t2 = np.arange(t1[0], t1[-1], 1.0/sample_rate)

        data = np.interp(t2, t1, filt.data)
        
        if self._meta['sample_rate'] is not None:
            return self.copy(data=data, sample_rate=sample_rate)
        elif self._meta['dt'] is not None:
            dt = self.dt * self.sample_rate / sample_rate
            return self.copy(data=data, dt=dt)

    def time_slice(self, start, stop):
        """Return a view of this trace with a specified start/stop time.
        
        Times are given relative to t0, and may be None to specify the
        beginning or end of the trace.
        """
        if self.regularly_sampled:
            i1 = int(np.round((start - self.t0) / self.dt)) if start is not None else None
            i2 = i1 + int(np.round((stop - start) / self.dt)) if stop is not None else None
        else:
            i1 = np.argwhere(self.time_values >= start)[0,0] if start is not None else None
            i2 = np.argwhere(self.time_values >= stop)[0,0] if stop is not None else None
        return self[i1:i2]

    def value_at(self, t, interp='linear'):
        """Return the value of this trace at specific timepoints.
        """
        return np.interp(t, self.time_values, self.data)

    def __mul__(self, x):
        return self.copy(data=self.data * x)

    def __truediv__(self, x):
        return self.copy(data=self.data / x)

    def __add__(self, x):
        return self.copy(data=self.data + x)

    def __sub__(self, x):
        return self.copy(data=self.data - x)

    def mean(self):
        """Mean value of the data in this Trace.

        Equivalent to self.data.mean()
        """
        return self.data.mean()

    def std(self):
        """Standard deviation of the data in this Trace.

        Equivalent to self.data.std()
        """
        return self.data.std()

    def median(self):
        """Median value of the data in this Trace.

        Equivalent to np.median(self.data)
        """
        return np.median(self.data)


class TraceView(Trace):
    def __init__(self, trace, sl):
        self._parent_trace = trace
        self._view_slice = sl
        inds = sl.indices(len(trace))
        data = trace.data[sl]
        meta = trace.meta.copy()
        if trace.has_time_values:
            meta['time_values'] = trace.time_values[sl]
        elif trace.has_timing:
            meta['t0'] = trace.t0 + inds[0] * trace.dt
            
        Trace.__init__(self, data, recording=trace.recording, **meta)

    @property
    def parent(self):
        return self._parent_trace

    @property
    def source_indices(self):
        """Return the indices of this view on the original Trace.
        """
        v = self
        start = 0
        while True:
            start += self._view_slice.start
            v = v.parent
            if not isinstance(v, TraceView):
                break
        return start, start + len(self)


class TraceList(object):
    def __init__(self, traces=None):
        self.traces = []
        if traces is not None:
            self.extend(traces)
            
    def __len__(self):
        return len(self.traces)
    
    def __iter__(self):
        return self.traces.__iter__()
    
    def __getitem__(self, i):
        return self.traces.__getitem__(i)
    
    def append(self, trace):
        self.traces.append(trace)
        
    def extend(self, traces):
        self.traces.extend(traces)
        
    def mean(self):
        """Return a trace with data averaged from all traces in this group.

        Downsamples to the minimum rate and clips ragged edges.
        """
        min_sr = min([trace.sample_rate for trace in self.traces])
        downsampled = [trace.resample(min_sr) for trace in self.traces]
        start_t = max([trace.t0 for trace in downsampled])
        stop_t = min([trace.time_values[-1] for trace in downsampled])
        array = []
        for trace in downsampled:
            clip_trace = trace.time_slice(start_t, stop_t)
            array.append(clip_trace.data)
        avg = np.nanmean(np.vstack(array), axis=0)
        
        return downsampled[0].copy(data=avg, t0=start_t, sample_rate=min_sr, dt=None)


class DAQRecording(Recording):
    """Input from / output to multiple channels on a data acquisition device.

    * Multiple channels of synchronized data (for each time point, one sample exists on every channel)
    * Metadata about DAQ state (sample rate, resolution, limits, filtering, etc)
    """


class ImageRecording(Recording):
    """Recording of one or more frames from a 2D imaging device (camera, 2p, confocal, etc).
    """


class VolumeRecording(Recording):
    """Recording of one or more frames from a 3D imaging device (MRI, lightfield, tomography, etc).
    """




