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
    def __init__(self, feed, instrument, hurstPeriod, calibratedStdMultiplier, calibratedShortMomentumPeriod, calibratedLongMomentumPeriod):
        strategy.BacktestingStrategy.__init__(self, feed)
        self.__longerMomentumPeriod =  calibratedLongMomentumPeriod
        self.__shortMomentumPeriod = calibratedShortMomentumPeriod
        self.__instrument = instrument
        self.__hurstPeriod = hurstPeriod
        self.__calibratedStdMultiplier = calibratedStdMultiplier
        self.__position = None
        # Use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self.__adjClosePrices = feed[instrument].getAdjCloseDataSeries()
        self.__prices = feed[instrument].getPriceDataSeries()
        self.__hurst = hurst.HurstExponent(self.__adjClosePrices, hurstPeriod)


        self.__longerEMA = ma.EMA(self.__prices, self.__longerMomentumPeriod)
        self.__shorterEMA = ma.EMA(self.__prices, self.__shortMomentumPeriod)
        self.__bollingerBandsPeriod = 30
        self.__bollingerBands = bollinger.BollingerBands(feed[instrument].getCloseDataSeries(), self.__bollingerBandsPeriod, 2)
        self.__macd = macd.MACD(feed[instrument].getCloseDataSeries(),9,16,6)

    def getHurst(self):
        return self.__hurst

    def getHurstValue(self):
        value = self.__hurst.getEventWindow().getValue()
        return value if value else 0.5

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f " % (execInfo.getPrice()))

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f " % (execInfo.getPrice()))

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

    def onBars(self, bars):
        #self.__halfLifeHelper.update()
        if bars.getBar(self.__instrument):
            hurst = self.getHurstValue()
            #halfLife = self.__halfLifeHelper.getHalfLife()
            #stdDev = self.__halfLifeHelper.getStdDev()
            #ma = self.__halfLifeHelper.getSma()
            bar = bars[self.__instrument]
            open = bar.getOpen()
            close = bar.getAdjClose()
            currentPos = abs(self.getBroker().getShares(self.__instrument))

            lowerBBands = self.__bollingerBands.getLowerBand()[-1]
            upperBBands = self.__bollingerBands.getUpperBand()[-1]

            macdLine = self.__macd
            signalLine = self.__macd.getSignal()

            if hurst is not None:
                if hurst < 0.5:
                    if close < lowerBBands > 0:
                        self.buy(bars)

                    elif close > upperBBands and currentPos > 0:
                        self.sell(bars)

                if hurst > 0.5:
                    if cross.cross_above(macdLine, signalLine) > 0:
                        self.buy(bars)

                    if cross.cross_below(macdLine, signalLine) > 0 and currentPos > 0:
                        self.sell(bars)