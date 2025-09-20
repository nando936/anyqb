from process_inbox import InboxProcessor
processor = InboxProcessor()

# Process the Shell receipt
filename = 'Scan - 2025-09-16 12_11_06.pdf'
file_path = processor.inbox_path + '\\' + filename

# Extract text
text = processor.extract_text_from_pdf(file_path)

# Extract receipt data
receipt_data = processor.extract_receipt_data(text, filename)

# Display what was found
print('='*60)
print(f'PROCESSING: {filename}')
print('='*60)
print(f'Vendor: {receipt_data["vendor"] or "[NOT FOUND]"}')
print(f'Date: {receipt_data["date"] or "[NOT FOUND]"}')
if receipt_data['amount']:
    print(f'Amount: ${receipt_data["amount"]:.2f}')
else:
    print('Amount: [NOT FOUND]')

if receipt_data['payment_card_last4']:
    print(f'Payment: {receipt_data["payment_method"]} ending {receipt_data["payment_card_last4"]}')
else:
    print(f'Payment: {receipt_data["payment_method"] or "[NOT FOUND]"}')

if receipt_data['bank_account']:
    print(f'Bank Account: {receipt_data["bank_account"]} [AUTO-MAPPED]')
else:
    print('Bank Account: [NEEDS MAPPING]')

if receipt_data['line_items']:
    print('\nLine Items Found:')
    for item in receipt_data['line_items']:
        print(f'  - {item["description"]}: ${item["amount"]:.2f}')

print('\n--- INFORMATION EXTRACTED ---')
print('Now I need to ask you for Job/Customer and QB Item...')