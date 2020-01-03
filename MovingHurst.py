from pyalgotrade import technical
from hurst import compute_Hc
import numpy as np

class HurstExponentEventWindow(technical.EventWindow):
    def __init__(self, period, minLags, maxLags, logValues=True):
        super(HurstExponentEventWindow, self).__init__(period)
        self.__minLags = minLags
        self.__maxLags = maxLags
        self.__logValues = logValues

    def onNewValue(self, dateTime, value):
        if value is not None and self.__logValues:
            value = np.log10(value)
        super(HurstExponentEventWindow, self).onNewValue(dateTime, value)

    def getValue(self):
        ret = None
        if self.windowFull():
            ret = compute_Hc(self.getValues(), kind='price')[0]
        return ret


class HurstExponent(technical.EventBasedFilter):
    """Hurst exponent filter based on technical.EventBasedFilter
    :param dataSeries: The DataSeries instance
    :type dataSeries: :class:`pyalgotrade.dataseries.DataSeries`
    :param period: The number of values to use to calculate the hurst exponent
    :type period: int
    :param minLags: The minimum number of lags to use. Must be >= 2
    :type minLags: int
    :param maxLags: The maximum number of lags to use. Must be > minLags
    :type maxLags: int
    :param maxLen: The maximum number of values to hold
        Once a bounded length is full, when new items are added, a corresponding number of items are discarded
        from the opposite end. If None then dataseries.DEFAULT_MAX_LEN is used
    :type maxLen: int
    """

    def __init__(self, dataSeries, period, minLags=2, maxLags=20, logValues=True, maxLen=None):
        assert period > 0, "period must be > 0"
        assert minLags >= 2, "minLags must be >= 2"
        assert maxLags > minLags, "maxLags must be > minLags"

        super(HurstExponent, self).__init__(
            dataSeries,
            HurstExponentEventWindow(period, minLags, maxLags, logValues),
            maxLen
        )