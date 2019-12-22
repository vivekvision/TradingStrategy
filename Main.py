from pyalgotrade import strategy
from pyalgotrade.technical import hurst
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade import plotter
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.stratanalyzer import returns

from pyalgotrade.stratanalyzer import drawdown

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import dataseries
from pyalgotrade.dataseries import aligned
from pyalgotrade import eventprofiler
from pyalgotrade.technical import stats
from pyalgotrade.technical import roc
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross


import numpy as np
from scipy.ndimage.interpolation import shift
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

import StrategyUtil

def main(plot):
    # Load  bar feed from CSV file/Yahoo format
    feed = yahoofeed.Feed()

    # instrument = "n225"
    # feed.addBarsFromCSV(instrument, r".\n225.csv")

    # instrument = "hsi"
    # feed.addBarsFromCSV(instrument, r".\hsi.csv")

    instrument = "twii"
    feed.addBarsFromCSV(instrument, r".\twii.csv")

    calibratedStdMultiplier = 0.5
    calibratedShortMomentumPeriod = 12
    calibratedLongMomentumPeriod = 26
    hurstPeriod = 120
    strat = StrategyUtil.ComprehensiveStrategy(feed, instrument, hurstPeriod, calibratedStdMultiplier, calibratedShortMomentumPeriod, calibratedLongMomentumPeriod)

    #Attach a Sharpe Ratio analyser
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    strat.attachAnalyzer(sharpeRatioAnalyzer)

    #Attach a Draw Down analyzer
    drawdownAnalyzer = drawdown.DrawDown()
    strat.attachAnalyzer(drawdownAnalyzer)

    # Attach a return analyzer
    returnsAnalyzer = returns.Returns()
    strat.attachAnalyzer(returnsAnalyzer)

    if plot:
        plt = plotter.StrategyPlotter(strat, True, False, True)
        plt.getOrCreateSubplot("hurst").addDataSeries("Hurst", strat.getHurst())
        plt.getOrCreateSubplot("hurst").addLine("Random", 0.5)

        # Plot the simple returns on each bar.
        plt.getOrCreateSubplot("returns").addDataSeries("Simple returns", returnsAnalyzer.getReturns())

    strat.run()
    strat.info("Final portfolio value: $%.2f" % strat.getResult())
    print("Sharpe ratio: %.2f" % sharpeRatioAnalyzer.getSharpeRatio(0.05))
    print("Maximum Drawdown : %.2f" % drawdownAnalyzer.getMaxDrawDown())
    print("Longest Drawdown Duration : %s" % drawdownAnalyzer.getLongestDrawDownDuration())
    print("Cumulative returns: %.2f %%" % (returnsAnalyzer.getCumulativeReturns()[-1] * 100))

    if plot:
        plt.plot()

if __name__ == "__main__":
    main(True)
