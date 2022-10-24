import discord
import yfinance as yf
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name="type !help"))
    print("Logged in as {0.user}".format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!help"):
        await message.channel.send("\
        :money_with_wings: Get stock price: !get {stock symbol}\n:date: Get stock price on specific date: !get {stock symbol} {date: YYYY-MM-DD)\n:scissors: Get most recent stock split: !split {stock symbol}")

    if message.content.startswith("!get"):
        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)
        if len(message.content.split(' ')) == 2:
            negativeFlag = False
            price = stock.info['regularMarketPrice']
            try:
                if len(str(price).split('.', 1)[1]) < 2: # always have 2 decimals in price, ex. $1.1 to $1.10
                    price = format(price, ".2f")
            except IndexError:
                await message.channel.send(":no_entry_sign: An error has occured. Check the spelling of the stock ticker and try again.")
            pastPrice = stock.info['previousClose']
            priceChange = float(price) - pastPrice
            if priceChange < 0:
                priceChange *= -1
                negativeFlag = True
            priceChangePercent = round(priceChange / pastPrice * 100, 2)
            if float(price) < 1: # is price is < $1, use 4 decimal places in price change
                if priceChange < 0:
                    negativeFlag = True
                priceChange = format(priceChange, ".4f")
            else:
                priceChange = round(priceChange, 2) # round after the percent is calculated to get the correct percent
            if negativeFlag:
                await message.channel.send(f"${stockName.upper()} = ${price} \n-${priceChange} :chart_with_downwards_trend: \n{priceChangePercent*-1}%")
            else:
                await message.channel.send(f"${stockName.upper()} = ${price} \n+${priceChange} :chart_with_upwards_trend: \n+{priceChangePercent}%")      

        else:
            date = str(message.content.split(' ')[2])
            dates = date.split('-')
            endDate = int(dates[2]) + 1
            if endDate < 10:
                endDates = dates[0] + '-' + dates[1] + '-' + '0' + str(endDate)
            else:
                endDates = dates[0] + '-' + dates[1] + '-' + str(endDate)
            historyDF = stock.history(start=date, end=endDates, interval="1d", actions=False)
            if historyDF.empty:
                await message.channel.send(":no_entry_sign: An error has occured. Ensure that the selected date is a business day and try again.")
            else:
                historicalPrice = float(historyDF.iloc[0]["Close"])
                if historicalPrice < 1: # if price is lower than $1, round to 4 decimals
                    historicalPrice = format(historicalPrice, ".4f")
                else: # if price is greater than or equal to 1, round to 2 decimals
                    historicalPrice = format(historicalPrice, ".2f")
                currentPrice = format(stock.info['regularMarketPrice'])
                percentChange = round((float(currentPrice) - float(historicalPrice)) / float(historicalPrice) * 100, 2)
                if float(currentPrice) >= float(historicalPrice):
                    await message.channel.send(f"The price of ${stockName.upper()} on {date} was ${historicalPrice}. Today, ${stockName.upper()} is worth ${currentPrice}, a {percentChange}% increase :chart_with_upwards_trend:")
                else:
                    percentChange *= -1
                    await message.channel.send(f"The price of ${stockName.upper()} on {date} was ${historicalPrice}. Today, ${stockName.upper()} is worth ${currentPrice}, a {percentChange}% decrease :chart_with_downwards_trend:")

    if message.content.startswith("!splits"):
        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)
        splitsDF = stock.splits
        if splitsDF.empty:
            await message.channel.send(f":no_entry_sign: ${stockName.upper()} has never had a stock split.")
        else:
            date = str(splitsDF.head().index[-1]).split(' ', 1)[0] # get date from pandas dataframe
            split = float(splitsDF[-1])
            if split < 1:
                split = 1 / split
                await message.channel.send(f"${stockName.upper()} had a 1 - {split} split on {date}.")
            else:
                await message.channel.send(f"${stockName.upper()} had a {split} - 1 split on {date}.")


#client.run(<bot token>)