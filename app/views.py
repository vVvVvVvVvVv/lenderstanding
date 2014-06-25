from flask import Flask, render_template, request, jsonify
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
#@app.route('/index')
#def index():
#    # name = 'Vanessa Heckman'
#    # return 'Hello, World {0}'.format(name)
#    # Renders index.html.
#    return render_template('index.html')
#'''
from app.helpers.database import con_db, query_db
from app.helpers.filters import format_currency
import jinja2

#Change sql to 0.0.0.0
def sqlExec(query):
    db = MySQLdb.connect(user="root", host="localhost", port=3306, db='semfundc_zidisha')
    with db:
        cur = db.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(query)
        tables = cur.fetchall()
        return tables

@app.route("/")
def hello():
    ifexists = 0
    while ifexists ==0:
        rand_loanid = random.randint(0, 5000)
        cnt=sqlExec("SELECT COUNT(1) AS total FROM loanapplic WHERE loanid = %d;" % rand_loanid)
        ifexists = int(cnt[0]['total'])
        
    return render_template('index.html',rand_loanid=rand_loanid)

@app.route("/index.html")
def indexfn():
    ifexists = 0
    while ifexists ==0:
        rand_loanid = random.randint(0,5000)
        cnt=sqlExec("SELECT COUNT(1) AS total FROM loanapplic WHERE loanid = %d;" % rand_loanid)
        ifexists = int(cnt[0]['total'])    
    return render_template('index.html', rand_loanid=rand_loanid)

@app.route("/about.html")
def aboutfn():
    return render_template('about.html')

@app.route("/app")
def appfn():
    return render_template('app.html')

@app.route("/search.html")
def search():
    mydb = MySQLdb.connect(host="localhost", user="root", db = "semfundc_zidisha")
    cursor = mydb.cursor()

    loan_id = int(request.args.get("loan_id",None))

    pickle.dump( loan_id, open( "passloan.pkl", "wb" ))
    
    # loan_info = sqlExec("")
    loan_info=sqlExec("select sift_score, interest, period, applydate-borrowers.Created as time_to_complete from loanapplic join borrowers on loanapplic.borrowerid = borrowers.userid where loanid = %d;" % loan_id)
    
    #posted_date_months=loan_info[0]['applydate']
    
    #image_id_str = str(loan_info[0]['image_id'])
    
    # change country code to continent
    #continent_map = pickle.load( open( "continent_map.pkl", "rb" ) )
    #continent = continent_map[loan_info[0]['location_country_code']]
    
    #vectorize contients and sectors
    #(contdict,sectordict) = pickle.load( open( "contsect_dict.pkl", "rb" ) )
    #continent_vec = contdict[continent]
    #sector_vec = sectordict[loan_info[0]['sector']]
    
    #if loan_info[0]['borrowers_gender'] == 'F':
    #    borrowers_gender = 1
    #else:
    #    borrowers_gender=0

    #xin = np.append(continent_vec,sector_vec)
    #xin = np.append(xin,np.array( [borrowers_gender,loan_info[0]['description_num_languages'],loan_info[0]['loan_amount'],posted_date_months,loan_info[0]['terms_repayment_term'] ] ))
    
    print loan_info
    print '.....'
    print loan_info[0]
    
    #xin = np.asarray(loan_info[0])
    xin = np.array([0.52, 0.7, 12, 60.0*60*24])
    
    clf = pickle.load( open('app/helpers/model.pkl', "rb"))
    y = clf.predict(xin)[0]
    prob_fund = clf.predict_proba(xin)[0][1]
    
    loan_info = 'Lekjlejkels'
    y = 0
    
    if y == 0:
        ypred = 'Will pay back loan in full'
    elif y ==1:
        ypred = 'Will default on loan'


    # took out: image_id_str =image_id_str,
    return render_template('search.html',loan_id=loan_id, loan_info=loan_info, ypred=ypred, prob_fund=prob_fund)

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
