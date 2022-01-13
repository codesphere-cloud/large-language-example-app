from imutils.perspective import four_point_transform
import numpy as np
import pytesseract
from math import pi
import imutils
import cv2
import re
import pandas as pd
import json
from thefuzz import process as fuzzy_process

from itertools import tee, islice, chain
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.palettes import Category10
from bokeh.transform import cumsum

def pre_processing(image_input):
    orig = cv2.imread(image_input)
    image = orig.copy()
    image = imutils.resize(image, width=500)
    ratio = orig.shape[1] / float(image.shape[1])
    image =cv2.copyMakeBorder(image,10,10,10,10,cv2.BORDER_CONSTANT,value=[0,0,0])
    # convert the image to grayscale, blur it slightly, and then apply
    # edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5,), 0)
    edged = cv2.Canny(blurred, 75, 200)   
    # find contours in the edge map and sort them by size in descending
    # order
    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    # initialize a contour that   to the receipt outline
    receiptCnt = None
    # loop over the contours
    for c in cnts:
        # approximate the contour
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        # if our approximated contour has four points, then we can
        # assume we have found the outline of the receipt
        if len(approx) == 4:
            receiptCnt = approx
            break
    # if the receipt contour is empty then our script could not find the
    # outline and we should be notified
    if receiptCnt is None:
        raise Exception(("Could not find receipt outline. "
            "Try debugging your edge detection and contour steps."))
    # apply a four-point perspective transform to the *original* image to
    # obtain a top-down bird's-eye view of the receipt
    receipt = four_point_transform(orig, receiptCnt.reshape(4, 2) * ratio)

    return receipt


def ocr_receipt(receipt):

    # apply OCR to the receipt image by assuming column data, ensuring
    # the text is *concatenated across the row* (additionally, for your
    # own images you may need to apply additional processing to cleanup
    # the image, including resizing, thresholding, etc.)

    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Simon\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

    options = "--psm 4 -l deu"
    text = pytesseract.image_to_string(
        cv2.cvtColor(receipt, cv2.COLOR_BGR2RGB),
        config=options)

    # define a regular expression that will match line items that include
    # a price component
    pricePattern = r'([0-9]+\,[0-9]+|[€])'

    # Helper for iterations
    def previous_and_next(some_iterable):
        prevs, items, nexts = tee(some_iterable, 3)
        prevs = chain([None], prevs)
        nexts = chain(islice(nexts, 1, None), [None])
        return zip(prevs, items, nexts)

    item_list = [str(x) for x in text.split("\n") if x]

    # Attemp to connect multi line items 
    output_list = []
    for previous, row, nxt in previous_and_next(item_list):
        if re.search(pricePattern, row) is not None and re.search(pricePattern, str(previous)) is None:
            output_list.append(f'{previous} {row}')
        elif re.search(pricePattern, row) is not None:
            output_list.append(row)
        else:
            None

    # Build a Dataframe with the OCR result
    grocery_input = pd.DataFrame(output_list,columns=["full"])

    grocery_input["clean"]=grocery_input["full"].replace(to_replace=r'\s[A|B|C]\b',value="€", regex=True)
    # Extract total
    grocery_input[["description","total"]]=grocery_input["clean"].str.split(r'[0-9,]+€', expand=True, n=1)
    grocery_input["total"]=grocery_input["clean"].str.extract(r'([0-9,]+€)')
    # Extract quantity
    grocery_input["quantity"] = grocery_input["clean"].str.extract(r'([0-9,]+[x]\b)')
    grocery_input["quantity"]=grocery_input["quantity"].fillna(1)
    grocery_input["quantity"]=grocery_input["quantity"].replace(to_replace=r"x",value="", regex=True)
    grocery_input["quantity"]=pd.to_numeric(grocery_input["quantity"],downcast='integer')
    
    grocery_input = grocery_input.drop(["full","clean"], axis=1)

    return grocery_input



#grocery_mapping = pd.read_excel(r"grocery_mapping.xlsx", engine="openpyxl")




def match_and_merge(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, cutoff: int = 80):
    # adding empty row
    df2 = df2.append(pd.Series(dtype=np.float64), ignore_index=True)
    index_of_empty = len(df2) - 1

    # matching
    indexed_strings_dict = dict(enumerate(df2[col2]))
    matched_indices = set()
    ordered_indices = []
    scores = []
    for s1 in df1[col1]:
        match = fuzzy_process.extractOne(
            query=s1,
            choices=indexed_strings_dict,
            score_cutoff=cutoff
        )
        score, index = match[1:] if match is not None else (0.0, index_of_empty)
        matched_indices.add(index)
        ordered_indices.append(index)
        scores.append(score)

    # detect unmatched entries to be positioned at the end of the dataframe
    missing_indices = [i for i in range(len(df2)) if i not in matched_indices]
    ordered_indices.extend(missing_indices)
    ordered_df2 = df2.iloc[ordered_indices].reset_index()

    # merge rows of dataframes
    merged_df = pd.concat([df1, ordered_df2], axis=1)

    # adding the scores column and sorting by its values
    scores.extend([0] * len(missing_indices))
    merged_df["Similarity Ratio"] = pd.Series(scores) / 100
    #merged_df.sort_values("Similarity Ratio", ascending=False)

    merged_df["footprint"]=merged_df["quantity"]*merged_df["Typical footprint"]
    merged_df["footprint"] = merged_df["footprint"].round(0)
    merged_df = merged_df.drop(["index"], axis=1).dropna(subset=["Product", "description"])

    not_recognized = pd.DataFrame()
    not_recognized["Product"] = merged_df.loc[merged_df['Typical footprint'].isnull()][["description"]]

    return merged_df, not_recognized


def prepare_pie(category):
   
    category['angle'] = category['footprint']/category['footprint'].sum() * 2*pi
    category['color'] = Category10[len(category)]
    print(category)
    pie = figure(title = "Category composition",toolbar_location=None , tools="hover", tooltips="@Category: @footprint g co2e")

    pie.wedge(x=0, y=1, radius=0.6,
            start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
            line_color="white", fill_color='color', legend_field='Category', source=category)
    pie.axis.axis_label = None
    pie.axis.visible = False
    pie.grid.grid_line_color = None

    """
    categories = category['Category']
    radians = [math.radians(percent* 360) for percent in category['percentage']]
    start_angle = [math.radians(0)]
    prev = start_angle[0]
    for i in radians[:-1]:
        start_angle.append(i + prev)
        prev = i + prev
    end_angle = start_angle[1:] + [math.radians(0)]
    x = 0
    y = 0
    radius = 0.8
    color = ["red", "blue", "yellow","green","grey"]
    for i in range(len(categories)):
        pie.wedge(x, y, radius,
                    start_angle = start_angle[i],
                    end_angle = end_angle[i],
                    color = color[i],
                    legend_label = categories[i])    
    """
    return components(pie)
