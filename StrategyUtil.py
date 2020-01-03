from pyalgotrade import strategy

from pyalgotrade.technical import rsi
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross

from pyalgotrade.technical import macd

import MovingHurst

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


class ComprehensiveStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, hurstPeriod, macdShorterPeriod, macdLongerPeriod, macdSignalPeriod,  rsiPeriod, entrySMAPeriod, exitSMAPeriod,
                 overBoughtThreshold, overSoldThreshold):
        strategy.BacktestingStrategy.__init__(self, feed)

        self.__instrument = instrument
        self.__hurstPeriod = hurstPeriod

        # Use adjusted close values, if available, instead of regular close values.
        if feed.barsHaveAdjClose():
            self.setUseAdjustedValues(True)
        self.__priceDS = feed[instrument].getPriceDataSeries()
        self.__adjClose = feed[instrument].getAdjCloseDataSeries()

        self.__macdShorterPeriod = macdShorterPeriod
        self.__macdLongerPeriod = macdLongerPeriod
        self.__macdSignalPeriod = macdSignalPeriod
        self.__macd = macd.MACD(self.__adjClose, self.__macdShorterPeriod, self.__macdLongerPeriod, self.__macdSignalPeriod)

        self.__hurst = MovingHurst.HurstExponent(self.__adjClose, hurstPeriod)

        self.__entrySMA = ma.EMA(self.__priceDS, entrySMAPeriod)
        self.__exitSMA = ma.EMA(self.__priceDS, exitSMAPeriod)

        self.__rsi = rsi.RSI(self.__adjClose, rsiPeriod)
        self.__overBoughtThreshold = overBoughtThreshold
        self.__overSoldThreshold = overSoldThreshold

        self.__longPos = None
        self.__shortPos = None


    def getHurst(self):
        return self.__hurst

    def getHurstValue(self):
        value = self.__hurst.getEventWindow().getValue()
        return value if value else 0.5

    def onEnterOk(self, position):
        if self.__longPos == position:
            execInfo = position.getEntryOrder().getExecutionInfo()
            self.info("Enter Long order at $%.2f " % (execInfo.getPrice()))
        elif self.__shortPos == position:
            execInfo = position.getEntryOrder().getExecutionInfo()
            self.info("Enter Short order at $%.2f " % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        if self.__longPos == position:
            self.__longPos = None
        elif self.__shortPos == position:
            self.__shortPos = None


    def onExitOk(self, position):
        if self.__longPos == position:
            execInfo = position.getExitOrder().getExecutionInfo()
            self.info("Exit Long order at $%.2f" % (execInfo.getPrice()))
            self.__longPos = None
        elif self.__shortPos == position:
            execInfo = position.getExitOrder().getExecutionInfo()
            self.info("Exit Short order at $%.2f" % (execInfo.getPrice()))
            self.__shortPos = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        position.exitMarket()

    def isMomentumRegimeEnterLongSignal(self):
        return cross.cross_above(self.__macd, self.__macd.getSignal()) > 0

    def isMomentumRegimeExitLongSignal(self):
        return cross.cross_above(self.__macd, self.__macd.getSignal()) < 0 and not self.__longPos.exitActive()

    def isMomentumRegimeEnterShortSignal(self):
        return cross.cross_below(self.__macd, self.__macd.getSignal()) > 0

    def isMomentumRegimeExitShortSignal(self):
        return cross.cross_below(self.__macd, self.__macd.getSignal()) < 0 and not self.__shortPos.exitActive()

    def onBars(self, bars):
        # Wait for enough bars to be available to calculate SMA and RSI.
        if self.__exitSMA[-1] is None or self.__entrySMA[-1] is None or self.__rsi[-1] is None:
            return

        bar = bars[self.__instrument]
        hurst = self.getHurstValue()
        if hurst is None:
            self.meanRevRegimAlgo(bar)
        elif hurst < 0.5:
            self.meanRevRegimAlgo(bar)
        elif hurst > 0.5:
            self.meanRevRegimAlgo(bar)

    def momenRegimAlgo(self, bar):
        if self.__longPos is not None:
            if self.isMomentumRegimeExitLongSignal():
                self.__longPos.exitMarket()
        elif self.__shortPos is not None:
            if self.isMomentumRegimeExitShortSignal():
                self.__shortPos.exitMarket()

        if self.isMomentumRegimeEnterLongSignal():
            shares = int(self.getBroker().getCash() * 0.9 / bar.getPrice())
            self.__longPos = self.enterLong(self.__instrument, shares, True)

        if self.isMomentumRegimeEnterShortSignal():
            shares = int(self.getBroker().getCash() * 0.9 / bar.getPrice())
            self.__shortPos = self.enterShort(self.__instrument, shares, True)

    def meanRevRegimAlgo(self, bar):
        if self.__longPos is not None:
            if self.isMeanRevExitLongSignal():
                self.__longPos.exitMarket()
        elif self.__shortPos is not None:
            if self.isMeanRevExitShortSignal():
                self.__shortPos.exitMarket()
        else:
            if self.isMeanRevEnterLongSignal(bar):
                shares = int(self.getBroker().getCash() * 0.9 / bar.getPrice())
                self.__longPos = self.enterLong(self.__instrument, shares, True)
            elif self.isMeanRevEnterShortSignal(bar):
                shares = int(self.getBroker().getCash() * 0.9 / bar.getPrice())
                self.__shortPos = self.enterShort(self.__instrument, shares, True)


    def isMeanRevEnterLongSignal(self, bar):
        return bar.getPrice() > self.__entrySMA[-1] and self.__rsi[-1] <= self.__overSoldThreshold

    def isMeanRevExitLongSignal(self):
        return cross.cross_above(self.__priceDS, self.__exitSMA) and not self.__longPos.exitActive()

    def isMeanRevEnterShortSignal(self, bar):
        return bar.getPrice() < self.__entrySMA[-1] and self.__rsi[-1] >= self.__overBoughtThreshold

    def isMeanRevExitShortSignal(self):
        return cross.cross_below(self.__priceDS, self.__exitSMA) and not self.__shortPos.exitActive()
