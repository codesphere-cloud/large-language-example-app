from flask import render_template, flash
from flask_app.forms import SubmitReceiptForm
from flask_app.analysis import analyze_receipt
from flask_app import app
import base64


@app.route("/", methods=['GET', 'POST'])
def Home():
    form = SubmitReceiptForm()
    if form.validate_on_submit():
        file = form.receipt.data.read()
        results = analyze_receipt(file)
        image_64 = base64.b64encode(file).decode('utf-8')
        flash('Successfully analyzed receipt', 'success')
        return render_template('results.html', results=results, form = form, image_64=image_64)
    return render_template('home.html', form = form)



