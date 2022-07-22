from flask import render_template, flash
from flask.helpers import url_for
from flask_app import db
from flask_app.forms import SubmitReceiptForm
from flask_app.models import Receipt
from flask_app.analysis import match_and_merge, prepare_pie, azure_form_recognition, azure_form_recognition_test
from flask_app.embed import match_and_merge_ki, match_and_merge_combined
from flask_app.search import get_search_results
from werkzeug.utils import secure_filename
import os
import pandas as pd
from flask_app import app, db, api
from PIL import Image
from flask_restful import Resource, reqparse
import base64
from io import BytesIO
from datetime import datetime
import json

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
        ocr_result, store = azure_form_recognition(image_path)
        # Match with footprint data
        results = match_and_merge(ocr_result,grocery_mapping,"description","product",83)

        results = results.fillna(0)

        
        category = results.groupby('category').agg({'footprint': 'sum'})
        
        output = {
            "results": results["product"].to_list(),
            "footprint" : results["footprint"].to_list(),
            "description" : results["description"].to_list(),
            "quantity" : results["quantity"].to_list(),
            "total" : results["total"].to_list(),
            "typical_weight" : results["typical_weight"].to_list(),
            "category" : results["category"].to_list(),
            "footprint_per_g": (results["footprint_per_100g"]/100).to_list(),
            "store": store,
            "footprint_dairy" : int(category.iloc[:,0].get("Milchprodukte / Eier", 0)),
            "footprint_meat" : int(category.iloc[:,0].get("Fleisch / Fisch", 0)),
            "footprint_vegetables" : int(category.iloc[:,0].get("Obst / Gemüse", 0)),
            "footprint_drinks" : int(category.iloc[:,0].get("Getränke", 0)),
            "footprint_other" : int(category.iloc[:,0].get("Sonstiges", 0)),   
             }
        #print(output)
        return output, 201




@app.route("/", methods=['GET', 'POST'])
def Home():
    form = SubmitReceiptForm()
    if form.validate_on_submit():
        file = form.receipt.data
        #image = Image.open(file)
        image_64 = base64.b64encode(file.read())
        byte_data = base64.b64decode(image_64) 
        #image = ImageOps.exif_transpose(image)
        #stream = BytesIO(byte_data)        
        #image = Image.open(stream)
        #if image.mode in ("RGBA", "P"):
        #    image = image.convert("RGB") 
        filename = secure_filename(file.filename)
        assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        image_path = os.path.join(assets_dir, filename)
        #image.save(image_path, format='JPEG', quality=40)
        #receipt_request = Receipt(receipt_file = image_path)
        #db.session.add(receipt_request)
        #db.session.commit()

    
        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")

        if '.xlsx' in filename:
            items = pd.read_excel(image_path)
            results = match_and_merge(items,grocery_mapping,"description","product",75)

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
            ocr_result, store = azure_form_recognition_test(byte_data)

            # Match with footprint data
            #results = match_and_merge(ocr_result,grocery_mapping,"description","product",90)

            # KI Test
            #ocr_result['description'] = ["Auf dem Kassenzettel steht: " + string for string in ocr_result['description']] 
            with open('./search_embedding_dict.json', 'r') as f:
                embeddings = json.load(f)
            results = match_and_merge_combined(ocr_result,grocery_mapping,"description","product",embeddings,90)

            #results["description"] = [string[27:] for string in results["description"]]
            #print(store)
            #results.to_sql(name="results",con=db.engine, index=False, if_exists="append")

        # Output missed items

        #writer2 = pd.ExcelWriter("not_recognized.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace")
        #missed_item.to_excel(writer2,index=False, sheet_name=filename.split(".",1)[0])
        #writer2.save()

        # Calculate category percentages
        category = results.groupby('category').agg({'footprint': 'sum'})
        footprint_dairy = category.iloc[:,0].get("Milchprodukte / Eier", 0)
        footprint_meat = category.iloc[:,0].get("Fleisch / Fisch", 0)
        footprint_vegetables = category.iloc[:,0].get("Obst / Gemüse", 0)
        footprint_drinks = category.iloc[:,0].get("Getränke", 0)
        footprint_other = category.iloc[:,0].get("Sonstiges", 0)
        #print(footprint_meat)
        # Get pie chart
        script, div = prepare_pie(category)
        
        # Calculate total
        total = str(sum(category['footprint'])/1000).replace('.',',')

        # Calculate car equivalent
        car_eq = str(round(sum(category['footprint'])/250,2)).replace('.',',')
        shower_eq = str(round(sum(category['footprint'])/196,2)).replace('.',',')
        print(results)
        pd.set_option('display.float_format','{:.0f}'.format)
        flash('Successfully analyzed receipt', 'success')
        return render_template('results.html', results = results.to_dict(orient='records'), filename = str(file.filename), image_path = url_for('static', filename=f'assets/{filename}'), script = script, div = div, total = total, car_eq = car_eq, shower_eq = shower_eq, form = form)
    return render_template('home.html', form = form)
""

# For testing only - currently with aleph alpha KI

class AnalyzeReceiptTest(Resource):
    def post(self):
        args = parser.parse_args()
        
        byte_data = base64.b64decode(args["image"]) 
        #stream = BytesIO(byte_data)
        
        #img = Image.open(stream)
        #filename = secure_filename(str(datetime.now()))
        #assets_dir = os.path.join(os.path.dirname(app.instance_path),'flask_app' ,'static' ,'assets')    
        #image_path = os.path.join(assets_dir, filename)
        #img.save(image_path, format='PNG', quality=40)

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")
        ocr_result, store = azure_form_recognition_test(byte_data)
        ocr_result['description'] = ["Auf dem Kassenzettel steht: " + string for string in ocr_result['description']] 

        # Match with footprint data
        with open('./search_embedding_dict.json', 'r') as f:
            embeddings = json.load(f)
        results = match_and_merge_ki(ocr_result,grocery_mapping,"description",embeddings)
        results["description"] = [string[27:] for string in results["description"]]        

        results = results.fillna(0)

        
        category = results.groupby('category').agg({'footprint': 'sum'})
        
        output = {
            "results": results["product"].to_list(),
            "footprint" : results["footprint"].to_list(),
            "description" : results["description"].to_list(),
            "quantity" : results["quantity"].to_list(),
            "total" : results["total"].to_list(),
            "typical_weight" : results["typical_weight"].to_list(),
            "category" : results["category"].to_list(),
            "footprint_per_g": (results["footprint_per_100g"]/100).to_list(),
            "store": store,
            "footprint_dairy" : int(category.iloc[:,0].get("Milchprodukte / Eier", 0)),
            "footprint_meat" : int(category.iloc[:,0].get("Fleisch / Fisch", 0)),
            "footprint_vegetables" : int(category.iloc[:,0].get("Obst / Gemüse", 0)),
            "footprint_drinks" : int(category.iloc[:,0].get("Getränke", 0)),
            "footprint_other" : int(category.iloc[:,0].get("Sonstiges", 0)),   
             }
        #print(output)
        return output, 201


# Search api


search_parser = reqparse.RequestParser()
search_parser.add_argument('query', type=str, help='utf-8 encoded string',location='args')



class Search(Resource):
    def get(self):
        args = search_parser.parse_args()
        #print(args)
        query = args["query"]
        

        # Load mapping table
        grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")



        # Match with footprint data
        with open('./search_embedding_dict.json', 'r') as f:
            embeddings = json.load(f)
        result = get_search_results(query,grocery_mapping,"product",embeddings,90,50)
        

       
        #print(result)
        return result, 201



api.add_resource(AnalyzeReceiptTest, '/ApiTest')

api.add_resource(AnalyzeReceipt, '/Api')

api.add_resource(Search, '/Search')
