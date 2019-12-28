from pyalgotrade import strategy
from pyalgotrade.technical import hurst
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade import plotter
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import dataseries
from pyalgotrade.dataseries import aligned

from pyalgotrade import eventprofiler
from pyalgotrade.technical import stats
from pyalgotrade.technical import roc
from pyalgotrade.technical import rsi
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross

from pyalgotrade.technical import bollinger
from pyalgotrade.technical import macd

import numpy as np
from scipy.ndimage.interpolation import shift
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


class ComprehensiveStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, hurstPeriod, macdShorterPeriod, macdLongerPeriod, macdSignalPeriod, bollingerBandsPeriod, bollingerBandsNoOfStd):
        strategy.BacktestingStrategy.__init__(self, feed)

        self.__instrument = instrument
        self.__hurstPeriod = hurstPeriod

        self.__macdShorterPeriod = macdShorterPeriod
        self.__macdLongerPeriod = macdLongerPeriod
        self.__macdSignalPeriod = macdSignalPeriod
        self.__macd = macd.MACD(feed[instrument].getCloseDataSeries(), self.__macdShorterPeriod, self.__macdLongerPeriod, self.__macdSignalPeriod)

        # Use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self.__adjClosePrices = feed[instrument].getAdjCloseDataSeries()
        self.__prices = feed[instrument].getPriceDataSeries()
        self.__hurst = hurst.HurstExponent(self.__adjClosePrices, hurstPeriod)

        self.__bollingerBandsPeriod = bollingerBandsPeriod
        self.__bollingerBandsNoOfStd = bollingerBandsNoOfStd
        self.__bollingerBands = bollinger.BollingerBands(feed[instrument].getCloseDataSeries(), self.__bollingerBandsPeriod, self.__bollingerBandsNoOfStd)

        self.__longPos = None
        self.__shortPos = None


    def getHurst(self):
        return self.__hurst

    def getHurstValue(self):
        value = self.__hurst.getEventWindow().getValue()
        return value if value else 0.5

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f " % (execInfo.getPrice()))

    def onExitOk(self, position):
        if self.__longPos == position:
            execInfo = position.getExitOrder().getExecutionInfo()
            self.info("SELL-L at $%.2f" % (execInfo.getPrice()))
            self.__longPos = None
        elif self.__shortPos == position:
            execInfo = position.getExitOrder().getExecutionInfo()
            self.info("SELL-S at $%.2f" % (execInfo.getPrice()))
            self.__shortPos = None

    def sell(self, bars):
        currentPos = abs(self.getBroker().getShares(self.__instrument))
        if currentPos > 0:
            self.marketOrder(self.__instrument, currentPos * -1)
            self.info("Placing sell market order for %s shares" % currentPos)

    def buy(self, bars):
        cash = self.getBroker().getCash(False)
        price = bars[self.__instrument].getAdjClose()
        size = int((cash * 0.9 / price))
        self.info("Placing buy market order for %s shares" % size)
        self.marketOrder(self.__instrument, size)

    def isMeanReversionRegimeEnterLongSignal(self, close):
        return close < self.__bollingerBands.getLowerBand()[-1]

    def isMeanReversionRegimeExitLongSignal(self, close):
        return close >  self.__bollingerBands.getLowerBand()[-1] and not self.__longPos.exitActive()

    def isMeanReversionRegimeEnterShortSignal(self, close):
        return close > self.__bollingerBands.getUpperBand()[-1]

    def isMeanReversionRegimeExitShortSignal(self, close):
        return close < self.__bollingerBands.getUpperBand()[-1] and not self.__shortPos.exitActive()

    def isMomentumRegimeEnterLongSignal(self):
        return cross.cross_above(self.__macd, self.__macd.getSignal()) > 0

    def isMomentumRegimeExitLongSignal(self):
        return cross.cross_above(self.__macd, self.__macd.getSignal()) < 0 and not self.__longPos.exitActive()

    def isMomentumRegimeEnterShortSignal(self):
        return cross.cross_below(self.__macd, self.__macd.getSignal()) > 0

    def isMomentumRegimeExitShortSignal(self):
        return cross.cross_below(self.__macd, self.__macd.getSignal()) < 0 and not self.__shortPos.exitActive()


    def onBars(self, bars):
        if bars.getBar(self.__instrument):
            hurst = self.getHurstValue()

            bar = bars[self.__instrument]
            close = bar.getAdjClose()

            if hurst is not None:
                if hurst < 0.5:
                    if self.__longPos is not None:
                        if self.isMeanReversionRegimeExitLongSignal(close):
                            self.__longPos.exitMarket()
                    elif self.__shortPos is not None:
                        if self.isMeanReversionRegimeExitShortSignal(close):
                            self.__shortPos.exitMarket()

                    if self.isMeanReversionRegimeEnterLongSignal(close):
                        cash = self.getBroker().getCash() * 0.9
                        price = bars[self.__instrument].getAdjClose()
                        size = int(cash / price)
                        if size > 0:
                            self.__longPos = self.enterLong(self.__instrument, size, True)

                    elif self.isMeanReversionRegimeEnterShortSignal(close):
                        cash = self.getBroker().getCash() * 0.9
                        price = bars[self.__instrument].getAdjClose()
                        size = int(cash / price)
                        if size > 0:
                            self.__shortPos = self.enterShort(self.__instrument, size, True)

                if hurst > 0.5:
                    if self.__longPos is not None:
                        if self.isMomentumRegimeExitLongSignal():
                            self.__longPos.exitMarket()
                    elif self.__shortPos is not None:
                        if self.isMomentumRegimeExitShortSignal():
                            self.__shortPos.exitMarket()

                    if self.isMomentumRegimeEnterLongSignal():
                        cash = self.getBroker().getCash() * 0.9
                        price = bars[self.__instrument].getAdjClose()
                        size = int(cash / price)
                        if size > 0:
                            self.__longPos = self.enterLong(self.__instrument, size, True)

                    if self.isMomentumRegimeEnterShortSignal():
                        cash = self.getBroker().getCash() * 0.9
                        price = bars[self.__instrument].getAdjClose()
                        size = int(cash / price)
                        if size > 0:
                            self.__shortPos = self.enterShort(self.__instrument, size, True)
