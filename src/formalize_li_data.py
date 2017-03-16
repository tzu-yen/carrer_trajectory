#!/usr/bin/python
#-*- coding: utf-8 -*-

import unicodecsv
import sys
import os
import re
import psycopg2
import psycopg2.extras
import json
from datetime import date
import unicodedata

def get_db_conn(host='research01.cviwic8obgyy.us-east-1.rds.amazonaws.com', port='5432', db='research', user='tzuyen', pw='0610wang', autocommit=True):
    try:
        conn = psycopg2.connect(host=host, port=port, database=db, user=user, password=pw)
        conn.autocommit = autocommit
    except Exception as e:
        print str(e)
    return conn

def normalize_characters(string):
    # "áÁàÀâÂäÄåÅãÃçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔöÖõÕøØßúÚùÙûÛüÜ"
    # "aAaAaAaAaAaAcCeEeEeEeEiIiIiIiInNoOoOoOoOoOoObuUuUuUuU"
    if string:
        string = re.sub(u"’", "'", string)
        string = re.sub(u"Â", "", string)
        string = re.sub(u"ø", "o", string)
        string = re.sub(u"Ø", "O", string)
        string = re.sub(u"ß", "b", string)
        string = unicodedata.normalize("NFD", string).encode("ascii", "ignore")
    return string


def formalize_education(row):
    formalized_educations = []
    if not row:
        return formalized_educations
    digit_pattern = re.compile(r'\d')
    tmp = [e.strip() for e in row.decode('utf-8').split(' ; ') if e.strip()]
    seen = set()
    edu_lines = [edu_line for edu_line in tmp if edu_line not in seen and not seen.add(edu_line)]
    edu_seen = set()

    for edu_line in edu_lines:
        edu = {'school':None, 'field':None, 'degree':None, 'start_year':None, 'end_year':None}
        m = re.search(r"(\d{4,4})( - (\d{4,4}))?$", edu_line)
        if m:
            if m.group(2):
                edu['start_year'] = int(m.group(1))
                edu['end_year'] = int(m.group(3))
            else:
                edu['end_year'] = int(m.group(1))
            edu_context = edu_line[:edu_line.rfind(" ", 0, m.start()-1)]
        else:
            edu_context = edu_line
            
        edu_context_items = [ec.strip() for ec in edu_context.split('+')]
        edu['school'], edu_detail = (edu_context_items[0], edu_context_items[1].strip()) if len(edu_context_items)>=2 else (edu_context_items[0], "")
        double_major = False
        
        if edu_detail:
            edu_detail_items = [ed.strip() for ed in edu_detail.split(',') if ed.strip() and not digit_pattern.search(ed)]
            if len(edu_detail_items)==4:
                edu['degree'] = edu_detail_items[0] if not ' in ' in edu_detail_items[0] else edu_detail_items[0].split(' in ')[0]
                edu['field'] = edu_detail_item[1] if not ' in ' in edu_detail_items[1] else edu_detail_items[1].split(' in ')[1]
            elif len(edu_detail_items)==8:
                (edu['degree'], degree2, edu['field'], field2) = tuple(edu_detail_items[:4])
                if edu['degree'] == degree2 and edu['field'] != field2:
                    double_major = True
            elif len(edu_detail_items)==2:
                if edu_detail_items[0]!=edu_detail_items[1]:
                    edu['degree'] = edu_detail_items[0] if not ' in ' in edu_detail_items[0] else edu_detail_items[0].split(' in ')[0]
                    edu['field'] = edu_detail_item[1] if not ' in ' in edu_detail_items[1] else edu_detail_items[1].split(' in ')[1]
                elif " in " in edu_detail_item[0]:
                    edu['degree'], edu['field'] = edu_detail_item[0].strip().split(" in ")
                else:
                    edu['field'] = edu_detail_items[0]
            elif len(edu_detail_items)>=3:
                if not ' in ' in edu_detail_items[0]
                    edu['degree'] = edu_detail_items[0] 
                    edu['field'] = edu_detail_items[1]
                    if ' in ' in edu['field']:
                        edu['field'] = edu['field'].split(' in ')[1]
                else:
                    edu['degree'], edu['field'] = edu_detail_items[0].split(' in ')
            else:
                if ' in ' in edu_detail:
                    edu['degree'], edu['field'] = edu_detail.split(' in ')
                else:
                    edu['field'] = edu_detail
        if (edu['school'], edu['field'], edu['degree']) not in edu_seen:
            formalized_educations.append(edu)
            edu_seen.add((edu['school'], edu['field'], edu['degree']))

        if double_major and (edu['school'], field2, degree2) not in edu_seen:
            edu2 =  edu.copy()
            edu2['degree'], edu2['field'] = degree2, field2
            formalized_educations.append(edu2) 
            edu_seen.add((edu['school'], edu2['field'], edu2['degree']))
    
    return formalized_educations


def formalize_experience(row):
    formalized_experiences = []
    if not row:
        return formalized_experiences
    tmp = [line for line in row.split(' ; ') if line.strip()]
    seen = set()
    exp_lines = [exp_line for exp_line in tmp if exp_line not in seen and not seen.add(exp_line)]
    for exp_line in exp_lines:
        exp = {'title':None, 'company':None, 'is_current':False, 'start_year':None, 'end_year':None}
        m = re.search(r"(\d{4,4}) - (\d{4,4}|Present)", exp_line)
        if m:
            exp['start_year'] = int(m.group(1))
            if m.group(2) == 'Present':
                exp['end_year'] = date.today().year
                exp['is_current'] = True
            else:
                exp['end_year'] = int(m.group(2))
                exp['is_current'] = False
                
            exp_context = exp_line[:exp_line.rfind(" ", 0, m.start()-1)+1]
        else:
            exp_context = exp_line
        exp_details = [exp_detail.strip() for exp_detail in exp_context.split(' @ ') if exp_detail.strip()]

        if len(exp_details) == 2:
            exp['title'], exp['company'] = exp_details[0].decode('utf-8'), exp_details[1].decode('utf-8')
        else:
            exp['title'], exp['company'] = exp_details[0].decode('utf-8'), None
        formalized_experiences.append(exp)
    return formalized_experiences


def main(cursor, cursor2, lower, upper):
    cursor2.execute("SELECT id, educations, experiences FROM search.person_linkedin_profile WHERE id >= %s AND id <= %s AND NOT educations IS NULL AND NOT experiences IS NULL order by id;", (lower, upper))
    # cursor2.execute("SELECT * FROM search.person_linkedin_profile WHERE id in (225, 246, 528, 538, 4024934, 4042717);")
    counter = 0
    for data in cursor2:
        try:
            print '%d' % (data['id'])
            # picture_id = data['img_url'][7:data['img_url'].find('&')] if data['img_url'] else None
            experiences = formalize_experience(data['experiences']) if data['experiences'] else []
            educations = formalize_education(data['educations']) if data['educations'] else []
            if not __debug__:
                # cursor.execute("INSERT INTO profile.person (lnkd_url, name, location, industry, connections, picture_id, summary) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                #     (data['url'], data['name'], data['location'], data['industry'], data['connections'], picture_id, data['summary']))
                # profile_id = cursor.fetchone()[0]
                for edu in educations:
                    cursor.execute("INSERT INTO profile.education (profile_id, school, field, degree, start_year, end_year) VALUES (%s, %s, %s, %s, %s, %s);",
                        (data['id'], edu['school'], edu['field'], edu['degree'], edu['start_year'], edu['end_year']))
                for exp in experiences:
                    cursor.execute("INSERT INTO profile.position (profile_id, title, company, start_year, end_year, is_current) VALUES (%s, %s, %s, %s, %s, %s);",
                        (data['id'], exp['title'], exp['company'], exp['start_year'], exp['end_year'], exp['is_current']))
            else:
                # cursor.mogrify("INSERT INTO profile.person (name, lnkd_url, connections, summary, industry, location, picture_id) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                #     (data['name'], data['url'], data['connections'], data['summary'], data['industry'], data['location'], picture_id))
                for edu in educations:
                    cursor.mogrify("INSERT INTO profile.education (profile_id, school, field, degree, start_year, end_year) VALUES (%s, %s, %s, %s, %s, %s);",
                        (data['id'], edu['school'], edu['field'], edu['degree'], edu['start_year'], edu['end_year']))
                for exp in experiences:
                    cursor.mogrify("INSERT INTO profile.experience (profile_id, title, company, start_year, end_year, is_current) VALUES (%s, %s, %s, %s, %s, %s);",
                        (data['id'], exp['title'], exp['company'], exp['start_year'], exp['end_year'], exp['is_current']))
        except Exception as e:
            print str(e)
        finally:
            counter += 1
    print "%d profiles created." % counter 

if __name__ == "__main__":
    try:
        conn = get_db_conn()
        conn2 = get_db_conn(autocommit=False)
        if conn and conn2:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor2 = conn2.cursor('raw_data_cursor', cursor_factory=psycopg2.extras.DictCursor)
            main(cursor, cursor2, sys.argv[1], sys.argv[2])
    except Exception as e:
        print str(e)
    finally:
        cursor.close()
        cursor2.close()
        conn.close()
