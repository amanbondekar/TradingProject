import os
import csv
import json
from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
from django.conf import settings
from django.core.files.storage import default_storage

class Candle:
    def __init__(self, id, open, high, low, close, date):
        self.id = id
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.date = date

    def to_dict(self):
        return {
            'id': self.id,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'date': self.date,
        }

class UploadFileView(View):
    def get(self, request):
        return render(request, 'upload.html')

    def post(self, request):
        csv_file = request.FILES['file']
        timeframe = int(request.POST['timeframe'])

        # Ensure the uploaded_files directory exists
        uploaded_files_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
        if not os.path.exists(uploaded_files_dir):
            os.makedirs(uploaded_files_dir)

        # Save CSV file
        file_name = 'uploaded_files/' + csv_file.name
        file_path = default_storage.save(file_name, csv_file)
        full_file_path = default_storage.path(file_path)

        # Read CSV file
        candles = self.read_csv(full_file_path)

        # Convert candles to the given timeframe
        converted_candles = self.convert_timeframe(candles, timeframe)

        # Save JSON file
        json_file_path = self.save_json(converted_candles)

        # Create download response
        response = HttpResponse(json.dumps([candle.to_dict() for candle in converted_candles], indent=4), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename={os.path.basename(json_file_path)}'
        return response

    def read_csv(self, file_path):
        candles = []
        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            # Print the column names to debug
            print("CSV Column Names:", reader.fieldnames)
            # Trim whitespace from column names
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            print("Trimmed CSV Column Names:", reader.fieldnames)

            for idx, row in enumerate(reader):
                print(f"Row {idx}: {row}")  # Print each row to debug
                try:
                    date_time = f"{row['DATE']} {row['TIME']}"
                    candle = Candle(
                        id=idx,
                        open=float(row['OPEN']),
                        high=float(row['HIGH']),
                        low=float(row['LOW']),
                        close=float(row['CLOSE']),
                        date=date_time
                    )
                    candles.append(candle)
                except KeyError as e:
                    print(f"Missing column in CSV: {e}")
                    # Handle the missing column case appropriately
                    raise ValueError(f"Missing column in CSV: {e}")
        return candles


    def convert_timeframe(self, candles, timeframe):
        converted = []
        chunk_size = timeframe

        for i in range(0, len(candles), chunk_size):
            chunk = candles[i:i+chunk_size]
            if not chunk:
                continue
            open_price = chunk[0].open
            high_price = max(c.high for c in chunk)
            low_price = min(c.low for c in chunk)
            close_price = chunk[-1].close
            date_time = chunk[0].date  # assuming the date of the first candle in the chunk

            converted.append(Candle(id=i//chunk_size, open=open_price, high=high_price, low=low_price, close=close_price, date=date_time))

        return converted

    def save_json(self, candles):
        json_data = [candle.to_dict() for candle in candles]
        json_file_path = os.path.join(settings.MEDIA_ROOT, 'converted_data.json')
        with open(json_file_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        return json_file_path
