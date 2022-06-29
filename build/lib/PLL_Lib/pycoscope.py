import ctypes
from PLL_Lib.ps2000 import ps2000 as ps
from PLL_Lib.functions import adc2mV, mV2adc
import PLL_Lib.errorhelp as er
from PLL_Lib.display import ScopeDisplay
import warnings
import time
import numpy as np
import progressbar

voltage_range_strings = {
    '20mv': 1,
    '50mv': 2,
    '100mv': 3,
    '200mv': 4,
    '1v': 6,
    '2v': 7,
    '5v': 8,
    '10v': 9,
    '20v': 10,
}

voltage_ranges = [None, None, 0.02, 0.05, 0.1, 0.2, 1, 2, 5, 10]

time_units = {
    0: 1e-15,
    1: 1e-12,
    2: 1e-9,
    3: 1e-6,
    4: 1e-3,
    5: 1e0
}

time_per_sample_options = {
    '10ns': 1,
    '20ns': 2,
    '40ns': 3,
    '80ns': 4,
    '160ns': 5,
    '320ns': 6,
    '640ns': 7,
    '1micro_s': 8,
    '3micro_s': 9,
    '5micro_s': 10,
    '10micro_s': 11,
    '20micro_s': 12,
    '41micro_s': 13,
    '82micro_s': 14,
    '164micro_s': 15,
    '328micro_s': 16,
    '655micro_s': 17,
    '1ms': 18,
    '3ms': 19,
    '5ms': 20,
    '10ms': 21,
}

waveform_options = {
    'SINE': 0
}

max_adc = ctypes.c_int16(32767)
warning_threshold = 5
load_timeout = 7


def check_success(result, exceptiontype=er.LostConnectionException, errValue=0):
    if result == errValue:
        raise exceptiontype()
    return result


class PycoScope:
    def _check_with(f):
        def wrapper(self, *args, **kwargs):
            if not self._used_in_with:
                raise er.WrongContextException()
            return f(self, *args, **kwargs)

        return wrapper

    def __init__(self, *, time_per_sample='5micro_s', trigger_channel=None, voltage_range='1v', trigger_voltage=0.25,
                 rising_edge=True, trigger_offset=10, show_display=True, probe_10x=False):
        self._used_in_with = False
        self._probe_comp = 10 if probe_10x else 1
        vr_lower = voltage_range.lower()
        if vr_lower not in voltage_range_strings:
            raise er.InvalidVoltageRangeException(voltage_range, voltage_range_strings.keys())
        self._voltage_range = voltage_range_strings[vr_lower]
        self._voltage_range_volts = voltage_ranges[self._voltage_range]
        if time_per_sample not in time_per_sample_options:
            raise er.InvalidTimePerSampleException(time_per_sample, time_per_sample_options)
        self._time_text, self._timebase = time_per_sample, time_per_sample_options[time_per_sample]

        self._trigger_channel = trigger_channel
        self._trigger_offset = ctypes.c_int16(0)
        if trigger_channel is not None:
            if trigger_channel.upper() not in ('A', 'B'):
                raise er.InvalidTriggerChannelException(trigger_channel)
            if not type(trigger_offset) is int and 0 <= trigger_offset <= 100:
                raise er.InvalidTriggerOffsetException(trigger_offset)
            self._trigger_offset = ctypes.c_int16(-trigger_offset)
            self._trigger_voltage = trigger_voltage
            self._trigger_adc = int(max_adc.value * trigger_voltage / self._voltage_range_volts)
            if not 0 <= self._trigger_adc <= max_adc.value:
                raise er.InvalidTriggerVoltageException(trigger_voltage, self._voltage_range_volts, voltage_range)
            self._rising_edge = rising_edge

        self._show_display = show_display
        self._last_cap_time = -1

    def __enter__(self):
        self._used_in_with = True
        check_success(ps.ps2000_open_unit_async())
        self._chandle, progress = ctypes.c_int16(), ctypes.c_int16()
        start_time = time.time()
        with progressbar.ProgressBar(max_value=100, prefix='Loading Scope: ') as bar:
            while ps.ps2000_open_unit_progress(ctypes.byref(self._chandle), ctypes.byref(progress)) == 0:
                if time.time() - start_time > load_timeout: raise er.CouldNotFindScopeException()
                bar.update(progress.value)
        check_success(ps.ps2000PingUnit(self._chandle), er.CouldNotFindScopeException)

        # self._chandle = check_success(ps.ps2000_open_unit(), er.CouldNotFindScopeException)
        # enabled = 1, coupling type = PS2000_DC = 1, analogue offset = 0 V, channel = PS2000_CHANNEL_A = 0
        check_success(ps.ps2000_set_channel(self._chandle, 0, 1, 1, self._voltage_range))
        # same except channel = PS2000_CHANNEL_B = 1
        check_success(ps.ps2000_set_channel(self._chandle, 1, 1, 1, self._voltage_range))
        if self._trigger_channel is not None:
            channel_index = {'A': 0, 'B': 1}[self._trigger_channel.upper()]
            # last two are offset (in percent) and auto delay (in ms)
            check_success(
                ps.ps2000_set_trigger(self._chandle, channel_index, self._trigger_adc, int(not self._rising_edge),
                                      self._trigger_offset, 0))

        self._timeInterval, self._timeUnits, self._oversample = ctypes.c_int32(), ctypes.c_int32(), ctypes.c_int16(1)
        maxSamplesReturn = ctypes.c_int32()
        check_success(ps.ps2000_get_timebase(self._chandle, self._timebase, 8000, ctypes.byref(self._timeInterval),
                                             ctypes.byref(self._timeUnits), self._oversample,
                                             ctypes.byref(maxSamplesReturn)))
        self._max_samples = maxSamplesReturn.value

        # Set up display
        self._capture_time = self._max_samples * self._timeInterval.value * 1e-9  # Uses ns by default
        trigger_time = -self._capture_time*self._trigger_offset.value/100

        if self._show_display:
            self.display = ScopeDisplay(-self._voltage_range_volts * self._probe_comp,
                                        self._voltage_range_volts * self._probe_comp, -trigger_time,
                                        self._capture_time-trigger_time, self._time_text, self._max_samples, self._probe_comp,
                                        None if self._trigger_channel is None else self._trigger_voltage * self._probe_comp
                                        , 0)
        return self

    @_check_with
    def get_trace(self, status_text="Pass text using get_trace('status goes here')"):
        # self.max_samples = 2000
        oversample = ctypes.c_int16(1)
        cmaxSamples = ctypes.c_int32(self._max_samples)
        check_success(ps.ps2000PingUnit(self._chandle))
        timeIndisposedms = ctypes.c_int32()
        check_success(
            ps.ps2000_run_block(self._chandle, cmaxSamples, self._timebase, oversample, ctypes.byref(timeIndisposedms)))

        # Check for data collection to finish using ps5000aIsReady
        warned, start_time = False, time.time()

        while ps.ps2000_ready(self._chandle) == 0:
            if time.time() - start_time > warning_threshold and not warned:
                if self._trigger_channel is not None:
                    warnings.warn(er.trigger_warning(self._rising_edge, self._trigger_channel.upper()))
                else:
                    warnings.warn(er.wait_warning)
                warned = True
        time_buffer = (ctypes.c_int32 * self._max_samples)()
        bufferA = (ctypes.c_int16 * self._max_samples)()
        bufferB = (ctypes.c_int16 * self._max_samples)()
        overflow = ctypes.c_int16()

        check_success(ps.ps2000_get_times_and_values(self._chandle, ctypes.byref(time_buffer), ctypes.byref(bufferA),
                                                     ctypes.byref(bufferB), None, None,
                                                     ctypes.byref(overflow), self._timeUnits.value, cmaxSamples))
        captime = None
        if self._last_cap_time != -1:
            captime = time.time() - self._last_cap_time
        self._last_cap_time = time.time()

        # TODO overflow
        if overflow.value != 0 and not self._show_display:
            warnings.warn('Overflow!')

        arr_A, arr_B = np.array(bufferA, dtype=int), np.array(bufferB, dtype=int)
        volts_A = arr_A * self._voltage_range_volts / max_adc.value * self._probe_comp
        volts_B = arr_B * self._voltage_range_volts / max_adc.value * self._probe_comp
        times = np.array(time_buffer) * time_units[self._timeUnits.value]
        if self._show_display:
            self.display.set_status(status_text)
            self.display.update(times, volts_A, volts_B, captime, overflow.value != 0)
        return times, volts_A, volts_B

    @_check_with
    def set_signal_generator(self, frequency, wavetype='SINE', peak_to_peak_voltage=2, offset_voltage=0):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        stopStatus = ps.ps2000_stop(self._chandle)
        closeStatus = ps.ps2000_close_unit(self._chandle)
        if stopStatus == 0 or closeStatus == 0:
            warnings.warn(er.close_warning)
