from flask import render_template, flash
from flask.helpers import url_for
from flask_app import db
from flask_app.forms import SubmitReceiptForm
from flask_app.models import Receipt, Results
from flask_app.analysis import pre_processing, ocr_receipt, match_and_merge, prepare_pie
from werkzeug.utils import redirect, secure_filename
import os 
import pandas as pd
from flask_app import app, db



from bokeh.palettes import Category20c
from bokeh.plotting import figure, show
from bokeh.transform import cumsum



@app.route("/", methods=['GET', 'POST'])
def Home():
    form = SubmitReceiptForm()
    if form.validate_on_submit():
        file = form.receipt.data
        filename = secure_filename(file.filename)
        assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        image_path = os.path.join(assets_dir, filename)
        file.save(image_path)
        receipt_request = Receipt(receipt_file = image_path)
        db.session.add(receipt_request)
        db.session.commit()

        # Process the receipt
        receipt = pre_processing(image_path)

        # Ocr the receipt items
        ocr_result = ocr_receipt(receipt)

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")

        # Match with footprint data
        results, missed_item = match_and_merge(ocr_result,grocery_mapping,"description","Product",75)
        print(results)

        # Calculate category percentages
        category = results.groupby('Category').agg({'footprint': 'sum'})

        # Get pie chart
        script, div = prepare_pie(category)

        # Calculate total

        total = sum(category['footprint'])/1000

        pd.set_option('display.float_format','{:.0f}'.format)
        flash('Successfully analyzed receipt', 'success')
        return render_template('results.html', results = results.to_dict(orient='records'), filename = str(file.filename), image_path = url_for('static', filename=f'assets/{filename}'), script = script, div = div, total = total)
    return render_template('home.html', form = form)

