from flask_wtf import FlaskForm
from flask_wtf.file import  FileRequired, FileAllowed, FileField
from wtforms import SubmitField


class SubmitReceiptForm(FlaskForm):
   
    receipt = FileField("Possible inputs are jpeg, jpg or png files with less than 4mb. Make sure the receipt is well readable.",validators=[FileRequired(), FileAllowed(['jpeg','jpg','png', 'xlsx'],"Are you sure this was a jpg, jpeg or png file?")])

    submit = SubmitField('Analyze receipt')

                           
            
    