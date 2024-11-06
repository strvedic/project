from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
import yfinance as yf
import pandas as pd

class TradingSignalApp(App):
    def build(self):
        # Create the root layout
        root = FloatLayout()

        # Draw background color
        with root.canvas.before:
            Color(0.9, 0.9, 0.9, 1)  # Light gray color
            self.rect = Rectangle(size=root.size, pos=root.pos)

        # Update the background when resizing
        root.bind(size=self.update_rect, pos=self.update_rect)

        # Create main layout
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        root.add_widget(self.layout)

        # Input field for stock symbol
        self.stock_input = TextInput(hint_text="Enter Nifty 50 stock symbol (e.g., RELIANCE)", size_hint=(1, 0.1))
        self.layout.add_widget(self.stock_input)

        # Buttons layout
        button_layout = BoxLayout(size_hint=(1, 0.1))
        
        # Generate Signals button
        self.generate_button = Button(text="Generate Signals", background_color=(0.2, 0.5, 0.8, 1))
        self.generate_button.bind(on_press=self.generate_signals)
        button_layout.add_widget(self.generate_button)

        # Clear button
        self.clear_button = Button(text="Clear", background_color=(0.9, 0.3, 0.3, 1))
        self.clear_button.bind(on_press=self.clear_signals)
        button_layout.add_widget(self.clear_button)

        self.layout.add_widget(button_layout)

        # Scrollable area for signal information with markup enabled
        self.signal_scroll = ScrollView(size_hint=(1, 0.7))
        self.signal_label = Label(
            text="Enter a stock symbol and click 'Generate Signals' to view trading signals",
            size_hint_y=None,
            markup=True  # Enable markup for color customization
        )
        self.signal_label.bind(texture_size=self.update_text_height)
        self.signal_scroll.add_widget(self.signal_label)
        self.layout.add_widget(self.signal_scroll)

        return root

    def update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def generate_signals(self, instance):
        stock_symbol = self.stock_input.text.strip().upper()
        if not stock_symbol:
            self.signal_label.text = "[color=ff0000]Please enter a valid stock symbol.[/color]"
            return

        # Fetch stock data from yfinance
        try:
            data = yf.download(stock_symbol, period='1y')
            if data.empty:
                self.signal_label.text = f"[color=ff0000]Data for {stock_symbol} could not be found. Please try another stock.[/color]"
                return
        except Exception as e:
            self.signal_label.text = f"[color=ff0000]Error fetching data: {e}[/color]"
            return

        # Calculate signals and update the UI
        signals_text = f"[b][color=0000ff]{stock_symbol} Signals Summary:[/color][/b]\n\n"
        signals_text += self.calculate_signals(data)
        self.signal_label.text = signals_text

    def calculate_signals(self, data):
        # Moving Average Crossover Signal
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        data['MA_Signal'] = 0
        data.loc[data['MA50'] > data['MA200'], 'MA_Signal'] = 1  # Buy signal
        data.loc[data['MA50'] < data['MA200'], 'MA_Signal'] = -1  # Sell signal
        latest_ma_signal = self.get_latest_signal(data, 'MA_Signal', "Moving Average Crossover")

        # RSI Signal
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        RS = gain / loss
        data['RSI'] = 100 - (100 / (1 + RS))
        data['RSI_Signal'] = 0
        data.loc[data['RSI'] < 30, 'RSI_Signal'] = 1  # Buy when oversold
        data.loc[data['RSI'] > 70, 'RSI_Signal'] = -1  # Sell when overbought
        latest_rsi_signal = self.get_latest_signal(data, 'RSI_Signal', "RSI")

        # Bollinger Bands Signal
        data['20_MA'] = data['Close'].rolling(window=20).mean()
        data['Upper_Band'] = data['20_MA'] + (data['Close'].rolling(window=20).std() * 2)
        data['Lower_Band'] = data['20_MA'] - (data['Close'].rolling(window=20).std() * 2)
        data['BB_Signal'] = 0
        data.loc[data['Close'] > data['Upper_Band'], 'BB_Signal'] = -1  # Sell signal
        data.loc[data['Close'] < data['Lower_Band'], 'BB_Signal'] = 1  # Buy signal
        latest_bb_signal = self.get_latest_signal(data, 'BB_Signal', "Bollinger Bands")

        # MACD Signal
        data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = data['EMA12'] - data['EMA26']
        data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Signal'] = 0
        data.loc[data['MACD'] > data['Signal_Line'], 'MACD_Signal'] = 1  # Buy signal
        data.loc[data['MACD'] < data['Signal_Line'], 'MACD_Signal'] = -1  # Sell signal
        latest_macd_signal = self.get_latest_signal(data, 'MACD_Signal', "MACD")

        # Combine all signals
        signal_summary = f"{latest_ma_signal}\n\n{latest_rsi_signal}\n\n{latest_bb_signal}\n\n{latest_macd_signal}\n"
        return signal_summary

    def get_latest_signal(self, data, signal_column, strategy_name):
        latest_signal = data[signal_column].iloc[-1]
        signal_type = "Buy" if latest_signal == 1 else "Sell" if latest_signal == -1 else "Hold"
        entry_price = data['Close'].iloc[-1] if latest_signal in [1, -1] else None
        if entry_price:
            return f"[b][color=0000ff]{strategy_name} Signal:[/color][/b] [color=00cc00]{signal_type} at {entry_price:.2f}[/color]"
        return f"[b][color=0000ff]{strategy_name} Signal:[/color][/b] [color=ff6600]No recent signal[/color]"

    def clear_signals(self, instance):
        # Clear the input and signal label
        self.stock_input.text = ""
        self.signal_label.text = "Enter a stock symbol and click 'Generate Signals' to view trading signals"

    def update_text_height(self, instance, value):
        instance.height = instance.texture_size[1]

if __name__ == '__main__':
    TradingSignalApp().run()
