from database import Database

db = Database()

# Check courses with MMPC-001 and MMPC-002
print('=== Checking MMPC-001 courses ===')
result = db.get_courses_by_code_all('MMPC-001')
if result['success']:
    for course in result['courses']:
        print(f'ID: {course["id"]}, Code: {course["course_code"]}, Name: {course["course_name"]}')
        print(f'  EN: {course["pdf_filename_en"]}, HI: {course["pdf_filename_hi"]}, DEF: {course["pdf_filename"]}')
        print(f'  Program: {course["program"]}, Year: {course["year"]}, Semester: {course["semester"]}')
        print('---')
else:
    print('Error:', result['error'])

print('\n=== Checking MMPC-002 courses ===')
result = db.get_courses_by_code_all('MMPC-002')
if result['success']:
    for course in result['courses']:
        print(f'ID: {course["id"]}, Code: {course["course_code"]}, Name: {course["course_name"]}')
        print(f'  EN: {course["pdf_filename_en"]}, HI: {course["pdf_filename_hi"]}, DEF: {course["pdf_filename"]}')
        print(f'  Program: {course["program"]}, Year: {course["year"]}, Semester: {course["semester"]}')
        print('---')
else:
    print('Error:', result['error'])

# Test the course material resolution API
print('\n=== Testing course material resolution ===')
import requests

# Test MMPC-001 with English medium
try:
    response = requests.get('http://localhost:5000/api/course-material/MMPC-001?medium=english')
    print(f'MMPC-001 English: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'MMPC-001 English error: {e}')

# Test MMPC-001 with Hindi medium
try:
    response = requests.get('http://localhost:5000/api/course-material/MMPC-001?medium=hindi')
    print(f'MMPC-001 Hindi: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'MMPC-001 Hindi error: {e}')

# Test MMPC-002 with English medium
try:
    response = requests.get('http://localhost:5000/api/course-material/MMPC-002?medium=english')
    print(f'MMPC-002 English: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'MMPC-002 English error: {e}')

# Test MMPC-002 with Hindi medium
try:
    response = requests.get('http://localhost:5000/api/course-material/MMPC-002?medium=hindi')
    print(f'MMPC-002 Hindi: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'MMPC-002 Hindi error: {e}')
