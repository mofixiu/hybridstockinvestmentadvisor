import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_stock_history(ticker):
    file_path = f"data/processed/{ticker}_clean.csv"
    
    if not os.path.exists(file_path):
        print(f"Skipping {ticker} (No data)")
        return

    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date']) # Reload as datetime
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['close'], label=f'{ticker} Close Price', color='blue')
    plt.title(f"{ticker} - 5 Year Price History (NGX)")
    plt.xlabel("Year")
    plt.ylabel("Price (Naira)")
    plt.legend()
    plt.grid(True)
    
    # Save the plot (Great for your Thesis Chapter 3!)
    plt.savefig(f"{ticker}_plot.png")
    print(f"📈 Chart saved as {ticker}_plot.png")
    plt.show()

if __name__ == "__main__":
    # Test with one stock
    plot_stock_history("MTNN")