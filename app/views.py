from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from app import app, host, port, user, passwd, db
from app.helpers.database import con_db
import pymysql as MySQLdb
import pickle
import numpy as np
import dateutil.parser
import csv
import math
import random

# To create a database connection, add the following
# within your view functions:
# con = con_db(host, port, user, passwd, db)

# ROUTING/VIEW FUNCTIONS
#'''
#@app.route('/')
#'''
from app.helpers.database import con_db, query_db
from app.helpers.filters import format_currency
import jinja2

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'guest' and password == 'insight123'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

#Change sql to 0.0.0.0
def sqlExec(query):
    con = MySQLdb.connect(user=user, host=host, port=port, db=db)
    with con:
        cur = con.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(query)
        tables = cur.fetchall()
        return tables

@app.route("/")
@requires_auth
def hello():
    return render_template('index.html')
#ifexists = 0
#while ifexists ==0:
#    rand_loanid = random.randint(0, 5000)
#    cnt=sqlExec("SELECT COUNT(1) AS total FROM loanapplic WHERE loanid = %d;" % rand_loanid)
#    ifexists = int(cnt[0]['total'])

@app.route('/index.html')
def index():
    return render_template('index.html')#    # name = 'Vanessa Heckman'

@app.route("/about.html")
def aboutfn():
    return render_template('about.html')

@app.route("/search.html")
@requires_auth
def search():
    user = app.config["DATABASE_USER"]
    host = app.config["DATABASE_HOST"]
    port = app.config["DATABASE_PORT"]
    pw   = app.config["DATABASE_PASSWORD"]
    db   = app.config["DATABASE_DB"]
    
    # Need to change this on AWS:
    #con = MySQLdb.connect(user=user, host=host, port=port, pw = pw, db=db)
    con = MySQLdb.connect(user=user, host=host, port=port, db=db)
    cursor = con.cursor()

    # Loan ID
    loan_id = int(request.args.get("loan_id", None))
    pickle.dump( loan_id, open( "passloan.pkl", "wb"))
    
    # Load loan info
    loan_info = sqlExec("select sift_score, interest, period, applydate-borrowers.Created as time_to_complete from loanapplic join borrowers on loanapplic.borrowerid = borrowers.userid where loanid = %d;" % loan_id)
    
    # Sift score
    sift_score = loan_info[0]['sift_score']
    interest   = loan_info[0]['interest']
    period     = str(loan_info[0]['period'])
    time_to_complete = loan_info[0]['time_to_complete']
    
    # Features
    xin = np.array([sift_score, 0.7, period, 60.0*60*24])
    
    # Load model - Lin regression
    clf = pickle.load( open('app/helpers/model.pkl', "rb"))
    y = clf.predict(xin)[0]
    prob_fund = clf.predict_proba(xin)[0][1]

    # Make prediction
    if y == 0:
        ypred = 'Will pay back loan in full'
    elif y ==1:
        ypred = 'Will default on loan'

    # Set image id file
    image_id_str = "static/images/loan_images/" + str(loan_id) + ".jpg"
    return render_template('search.html',loan_id=loan_id, loan_info=loan_info, ypred=ypred, prob_fund=prob_fund, image_id_str =image_id_str)

@app.route("/eval.html")
def eval():
    #loan_id = pickle.load( open( "passloan.pkl", "rb" ))
    loan_id = 130
    
    loan_info=sqlExec("SELECT  name, borrowers_gender, location_country,location_country_code, sector, loan_amount, description_num_languages, posted_date, terms_repayment_term, image_id from Loans where loan_id = %d;" % loan_id)
    
    posted_date_months=loan_info[0]['posted_date'].month

    # change country code to continent
    continent_map = pickle.load( open( "continent_map.pkl", "rb" ) )
    continent = continent_map[loan_info[0]['location_country_code']]
    #vectorize contients and sectors
    (contdict,sectordict) = pickle.load( open( "contsect_dict.pkl", "rb" ) )
    continent_vec = contdict[continent]
    sector_vec = sectordict[loan_info[0]['sector']]
    
    if loan_info[0]['borrowers_gender'] == 'F':
        borrowers_gender = 1
    else:
        borrowers_gender=0


    clf = pickle.load( open( "model.pkl", "rb" ) )
    
    requested_loan_amount = loan_info[0]['loan_amount']
    requested_repayment_term = loan_info[0]['terms_repayment_term']
    binreqLoanAmount=int(round(loan_info[0]['loan_amount'],-2))/100

    if requested_repayment_term > 10:
        month_pred = [i for i in range(requested_repayment_term-10,requested_repayment_term+10)]
    else:
        month_pred = [(i+1) for i in range(20)]

    roundedReqAmt = int(math.floor(requested_loan_amount/100))

    if binreqLoanAmount >= 10:
        gridAmtSet = binreqLoanAmount
    else:
        gridAmtSet = 5

    amount_pred = [100*i for i in range(gridAmtSet-5,gridAmtSet+5)]
    
    #create list of tuples for (amount, month, funding prob )
    predMatrix=[]
    for amount in amount_pred:
        for month in month_pred:
            xin = np.append(continent_vec,sector_vec)
            xin = np.append(xin,np.array( [borrowers_gender,loan_info[0]['description_num_languages'],amount,posted_date_months,month ] ))


            predprob = round(clf.predict_proba(xin)[0][0],2)
            predMatrix.append((amount, month, predprob) )
    
    # write to tsv file
    ofile  = open('static/data.tsv', "wb")
    writer = csv.writer(ofile,delimiter='\t')

    writer.writerow(['day','hour', 'value'])
    for row in predMatrix:
                writer.writerow(row)
    ofile.close()

    amount_pred_str = str(amount_pred)
    month_pred_str = str(month_pred)

    return render_template('eval.html',loan_info=loan_info,loan_id=loan_id,roundedReqAmt=roundedReqAmt,requested_repayment_term=requested_repayment_term,gridAmtSet=gridAmtSet,amount_pred_str=amount_pred_str,month_pred_str=month_pred_str,binreqLoanAmount=binreqLoanAmount)


@app.route("/blocker")
def block():
    return "Blocked!"

@app.route('/<pagename>')
def regularpage(pagename = None):
    """
        Route not found by the other routes above.
        """
    return "You've arrived at : " + pagename
