from imutils.perspective import four_point_transform
import numpy as np
import pytesseract
import argparse
import imutils
import cv2
import re
import pandas as pd
from thefuzz import process as fuzzy_process

from itertools import tee, islice, chain

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
	help="path to input receipt image")
ap.add_argument("-d", "--debug", type=int, default=-1,
	help="whether or not we are visualizing each step of the pipeline")
args = vars(ap.parse_args())

# load the input image from disk, resize it, and compute the ratio
# of the *new* width to the *old* width
orig = cv2.imread(args["image"])
image = orig.copy()
image = imutils.resize(image, width=500)
image =cv2.copyMakeBorder(image,10,10,10,10,cv2.BORDER_CONSTANT,value=[0,0,0])
ratio = orig.shape[1] / float(image.shape[1])
# convert the image to grayscale, blur it slightly, and then apply
# edge detection
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = gray
edged = cv2.Canny(blurred, 75, 200)

# check to see if we should show the output of our edge detection
# procedure


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


# check to see if we should draw the contour of the receipt on the
# image and then display it to our screen
if args["debug"] > 0:
    output = image.copy()
    cv2.drawContours(output, [receiptCnt], -1, (0, 255, 0), 2)
    cv2.imshow("Input", image)
    cv2.imshow("Edged", edged)   
    cv2.imshow("Receipt Outline", output)
    cv2.waitKey(0)

# apply a four-point perspective transform to the *original* image to
# obtain a top-down bird's-eye view of the receipt
receipt = four_point_transform(orig, receiptCnt.reshape(4, 2) * ratio)
# show transformed image
cv2.imshow("Receipt Transform", imutils.resize(receipt, width=540))
cv2.waitKey(0)


# apply OCR to the receipt image by assuming column data, ensuring
# the text is *concatenated across the row* (additionally, for your
# own images you may need to apply additional processing to cleanup
# the image, including resizing, thresholding, etc.)

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Simon\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

options = "--psm 4 -l deu"
text = pytesseract.image_to_string(
	cv2.cvtColor(receipt, cv2.COLOR_BGR2RGB),
	config=options)

if args["debug"] > 0:
    print("[INFO] raw output:")
    print("==================")
    print(text)
    print("\n")

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
#print([type(x) for x in item_list])

#output_list = [row if (re.search(pricePattern, row) is not None) else f'{row} {nxt}' for previous, row, nxt in previous_and_next(item_list)]


# Attemp to connect multi line items 
output_list = []
for previous, row, nxt in previous_and_next(item_list):
    if re.search(pricePattern, row) is not None and re.search(pricePattern, str(previous)) is None:
        output_list.append(f'{previous} {row}')
    elif re.search(pricePattern, row) is not None:
        output_list.append(row)
    else:
        None



if args["debug"] > 0:
    print(output_list)


grocery_input = pd.DataFrame(output_list,columns=["full"])

grocery_input["clean"]=grocery_input["full"].replace(to_replace=r'\s[A|B|C]\b',value="€", regex=True)
# Extract total
grocery_input[["description","total"]]=grocery_input["clean"].str.split(r'[0-9,]+€', expand=True, n=1)
grocery_input["total"]=grocery_input["clean"].str.extract(r'([0-9,]+€)')
# Extract quantity
grocery_input["quantity"] = grocery_input["clean"].str.extract(r'([0-9,]+[x]\b)')
grocery_input["quantity"]=grocery_input["quantity"].fillna(1)
grocery_input["quantity"]=grocery_input["quantity"].replace(to_replace=r"x",value="", regex=True)
grocery_input["quantity"]=grocery_input["quantity"].apply(pd.to_numeric)


grocery_input = grocery_input.drop(["full","clean"], axis=1)
if args["debug"] > 0:
    print(grocery_input)

grocery_mapping = pd.read_excel(r"grocery_mapping.xlsx", engine="openpyxl")




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
    return merged_df.sort_values("Similarity Ratio", ascending=False)


    
# Merge the recognized items with the footprint data
merged = match_and_merge(grocery_input,grocery_mapping,"description","product",75).dropna(subset=["description"])
# Calculate footprint
merged["footprint"]=merged["quantity"]*merged["typical_footprint"]
merged = merged.drop(["index"], axis=1)
# Calculate success measure
total_items = len(merged.index)
recognized_items = merged.count(0)[5]
not_recognized = pd.DataFrame()
not_recognized["product"] = merged.loc[merged['typical_footprint'].isnull()][["description"]]
#merged.loc["Total"] = merged.sum(numeric_only=True)
print(merged)


# Save the output to Excel
output_name = "merged_output_"+args["image"].split(".",1)[0]+".xlsx"
writer = pd.ExcelWriter(output_name,engine="xlsxwriter")
merged.to_excel(writer, sheet_name='Result', index=False)
workbook  = writer.book
worksheet = writer.sheets['Result']
worksheet.insert_image('L2', args["image"],{'x_scale': 0.3, 'y_scale': 0.3})
writer.save()
print(f'[INFO] Recognized items: {recognized_items} out of {total_items}')
print(f'{output_name} sucessfully saved!')
print("========================")
# Append the not recognized item to the carbon database for manual review
print("Not recognized:")
print(not_recognized)
writer2 = pd.ExcelWriter("not_recognized.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace")
not_recognized.to_excel(writer2,index=False, sheet_name=args["image"].split(".",1)[0])
writer2.save()

