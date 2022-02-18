from flask import render_template, flash
from flask.helpers import url_for
from flask_app import db
from flask_app.forms import SubmitReceiptForm
from flask_app.models import Receipt, Results
from flask_app.analysis import match_and_merge, prepare_pie, azure_form_recognition
from werkzeug.utils import secure_filename
import os 
import pandas as pd
from flask_app import app, db, api
from PIL import Image, ImageOps
from flask_restful import Resource, reqparse
import base64
from io import BytesIO
from datetime import datetime
#from tempfile import NamedTemporaryFile

parser = reqparse.RequestParser()
parser.add_argument('image', help='Receipt image base64 encoded')

class AnalyzeReceipt(Resource):
    def post(self):
        args = parser.parse_args()
        
        byte_data = base64.b64decode(args["image"]) 
        stream = BytesIO(byte_data)
        
        img = Image.open(stream)
        filename = secure_filename(str(datetime.now()))
        assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        image_path = os.path.join(assets_dir, filename)
        img.save(image_path, format='JPEG', quality=40)

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")
        ocr_result = azure_form_recognition(image_path)
        # Match with footprint data
        results, missed_item = match_and_merge(ocr_result,grocery_mapping,"description","product",75)



        # Calculate category percentages
        category = results.groupby('category').agg({'footprint': 'sum'})

        # Get pie chart
        script, div = prepare_pie(category)
        
        # Calculate total
        total = str(sum(category['footprint'])/1000).replace('.',',')

        # Calculate car equivalent
        car_eq = str(round(sum(category['footprint'])/250,2)).replace('.',',')
        shower_eq = str(round(sum(category['footprint'])/196,2)).replace('.',',')
        print(results)
        print(results.to_json(orient='split'))
        return results.to_json(orient='split'), 201

api.add_resource(AnalyzeReceipt, '/Api')


@app.route("/", methods=['GET', 'POST'])
def Home():
    form = SubmitReceiptForm()
    if form.validate_on_submit():
        file = form.receipt.data
        image = Image.open(file)
        image = ImageOps.exif_transpose(image)
        filename = secure_filename(file.filename)
        assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        image_path = os.path.join(assets_dir, filename)
        image.save(image_path, format='JPEG', quality=40)
        receipt_request = Receipt(receipt_file = image_path)
        db.session.add(receipt_request)
        db.session.commit()

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")

        if '.xlsx' in filename:
            items = pd.read_excel(image_path)
            results ,missed_item = match_and_merge(items,grocery_mapping,"description","product",75)

        else:
            """
            # Old version without azure:
            # Process the receipt
            receipt = pre_processing(image_path)

            # Ocr the receipt items
            try:
                ocr_result = ocr_receipt(receipt)
            except ValueError:
                flash(Markup('It seems like our algorithm was unable to recognize the receipts structure or content, feel free to send us the picture via mail to <a href="mailto:receipt@project-count.com">receipt@project-count.com</a> we will get back to you as soon as possible.'), 'danger')
                return render_template('home.html', form = form)
            """
            ocr_result = azure_form_recognition(image_path)

            # Match with footprint data
            results, missed_item = match_and_merge(ocr_result,grocery_mapping,"description","product",75)
            
            results["request_id"] = Receipt.query.filter(Receipt.receipt_file == image_path).first().id
            results.to_sql(name="results",con=db.engine, index=False, if_exists="append")

        # Output missed items

        writer2 = pd.ExcelWriter("not_recognized.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace")
        missed_item.to_excel(writer2,index=False, sheet_name=filename.split(".",1)[0])
        writer2.save()

        # Calculate category percentages
        category = results.groupby('category').agg({'footprint': 'sum'})

        # Get pie chart
        script, div = prepare_pie(category)
        
        # Calculate total
        total = str(sum(category['footprint'])/1000).replace('.',',')

        # Calculate car equivalent
        car_eq = str(round(sum(category['footprint'])/250,2)).replace('.',',')
        shower_eq = str(round(sum(category['footprint'])/196,2)).replace('.',',')

        pd.set_option('display.float_format','{:.0f}'.format)
        flash('Successfully analyzed receipt', 'success')
        return render_template('results.html', results = results.to_dict(orient='records'), filename = str(file.filename), image_path = url_for('static', filename=f'assets/{filename}'), script = script, div = div, total = total, car_eq = car_eq, shower_eq = shower_eq, form = form)
    return render_template('home.html', form = form)




@app.route("/Api", methods=['POST'])
def Api():
    form = SubmitReceiptForm()
    if form.validate_on_submit():
        file = form.receipt.data
        image = Image.open(file)
        image = ImageOps.exif_transpose(image)
        filename = secure_filename(file.filename)
        assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        image_path = os.path.join(assets_dir, filename)
        image.save(image_path, format='JPEG', quality=40)
        receipt_request = Receipt(receipt_file = image_path)
        db.session.add(receipt_request)
        db.session.commit()

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")

        if '.xlsx' in filename:
            items = pd.read_excel(image_path)
            results ,missed_item = match_and_merge(items,grocery_mapping,"description","product",75)

        else:
            """
            # Old version without azure:
            # Process the receipt
            receipt = pre_processing(image_path)

            # Ocr the receipt items
            try:
                ocr_result = ocr_receipt(receipt)
            except ValueError:
                flash(Markup('It seems like our algorithm was unable to recognize the receipts structure or content, feel free to send us the picture via mail to <a href="mailto:receipt@project-count.com">receipt@project-count.com</a> we will get back to you as soon as possible.'), 'danger')
                return render_template('home.html', form = form)
            """
            ocr_result = azure_form_recognition(image_path)

            # Match with footprint data
            results, missed_item = match_and_merge(ocr_result,grocery_mapping,"description","product",75)
            
            results["request_id"] = Receipt.query.filter(Receipt.receipt_file == image_path).first().id
            results.to_sql(name="results",con=db.engine, index=False, if_exists="append")

        # Output missed items

        writer2 = pd.ExcelWriter("not_recognized.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace")
        missed_item.to_excel(writer2,index=False, sheet_name=filename.split(".",1)[0])
        writer2.save()

        # Calculate category percentages
        category = results.groupby('category').agg({'footprint': 'sum'})

        # Get pie chart
        script, div = prepare_pie(category)
        
        # Calculate total
        total = str(sum(category['footprint'])/1000).replace('.',',')

        # Calculate car equivalent
        car_eq = str(round(sum(category['footprint'])/250,2)).replace('.',',')
        shower_eq = str(round(sum(category['footprint'])/196,2)).replace('.',',')

    return results.to_dict(orient='records') 
