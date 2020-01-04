from pyalgotrade import technical

import numpy as np
from scipy.ndimage.interpolation import shift

import statsmodels.api as sm


class HalfLifeEventWindow(technical.EventWindow):
    def __init__(self, period,):
        super(HalfLifeEventWindow, self).__init__(period)

    def onNewValue(self, dateTime, value):
        super(HalfLifeEventWindow, self).onNewValue(dateTime, value)

    # Calculate half-life of mean reversion - Reference Chan(2013)
    def getValue(self):
        originalValues = np.array(self.getValues())
        shiftedValues = shift(originalValues, 1, cval=np.nan)
        shiftedValues[0] = shiftedValues[1]
        ret = originalValues - shiftedValues
        ret[0] = ret[1]
        shiftedValues2 = sm.add_constant(shiftedValues)

        model = sm.OLS(ret, shiftedValues2)
        res = model.fit()
        halflife = round(-np.log(2) / res.params[1], 0)
        return halflife

class ReversionHalfLife(technical.EventBasedFilter):
    """Mean Reversion Half Life  filter based on technical.EventBasedFilter
    :param dataSeries: The DataSeries instance
    :type dataSeries: :class:`pyalgotrade.dataseries.DataSeries`
    :param period: The number of values to use to calculate the hurst exponent
    :type period: int
    :param minLags: The minimum number of lags to use. Must be >= 2
    :type minLags: int
    :param maxLags: The maximum number of lags to use. Must be > minLags
    :type maxLags: int
    :param maxLen: The maximum number of values to hold
    :type maxLen: int
    """

    def __init__(self, dataSeries, period, minLags=2, maxLags=50, logValues=True, maxLen=None):
        assert period > 0, "period must be > 0"
        assert minLags >= 2, "minLags must be >= 2"
        assert maxLags > minLags, "maxLags must be > minLags"

        super(ReversionHalfLife, self).__init__(
            dataSeries,
            HalfLifeEventWindow(period),
            maxLen
        )