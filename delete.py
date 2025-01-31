import openai

# Initialize the client
client = openai.OpenAI(api_key='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')

# List files in your OpenAI storage
response = client.files.list()

# Initialize a counter for the total number of files
file_count = 0

# List to store file IDs for deletion
file_ids = []

# Iterate over the files and count them
for file in response:
    file_count += 1
    file_ids.append(file.id)
    print(f"ID: {file.id}, Filename: {file.filename}, Purpose: {file.purpose}")

# Print the total number of files
print(f"Total number of files: {file_count}")

# Ask user if they want to delete all files
delete_all = input("Would you like to delete all files? (Y/N): ").strip().upper()

if delete_all == 'Y':
    # Iterate over file IDs and delete each file
    for file_id in file_ids:
        client.files.delete(file_id)
        print(f"Deleted file with ID: {file_id}")
    print("All files have been deleted.")
else:
    print("No files were deleted.")