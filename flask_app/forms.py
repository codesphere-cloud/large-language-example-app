from flask_wtf import FlaskForm
from flask_wtf.file import  FileRequired, FileAllowed, FileField
from wtforms import SubmitField


class SubmitReceiptForm(FlaskForm):
   
    receipt = FileField("",validators=[FileRequired(), FileAllowed(['jpeg','jpg','png'],"Are you sure this was a jpg, jpeg or png file?")])

    submit = SubmitField('Analyze receipt')

                           
            
    