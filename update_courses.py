from database import Database

db = Database()

# Update MMPC-001 to have English and Hindi PDFs
print('=== Updating MMPC-001 ===')
result = db.update_course(
    course_id=1,
    pdf_filename_en='MMPC-001-EN.pdf',
    pdf_filename_hi='MMPC-001-HI.pdf'
)
print('Update result:', result)

# Update MMPC-002 to have English and Hindi PDFs
print('\n=== Updating MMPC-002 ===')
result = db.update_course(
    course_id=2,
    pdf_filename_en='MMPC-002-EN.pdf',
    pdf_filename_hi='MMPC-002-HI.pdf'
)
print('Update result:', result)

# Verify the updates
print('\n=== Verifying updates ===')
result = db.get_courses_by_code_all('MMPC-001')
if result['success']:
    for course in result['courses']:
        print(f'MMPC-001: EN={course["pdf_filename_en"]}, HI={course["pdf_filename_hi"]}, DEF={course["pdf_filename"]}')

result = db.get_courses_by_code_all('MMPC-002')
if result['success']:
    for course in result['courses']:
        print(f'MMPC-002: EN={course["pdf_filename_en"]}, HI={course["pdf_filename_hi"]}, DEF={course["pdf_filename"]}')
