# import openai
# from dateutil.parser import parse
# import pytz
#
# # Set your OpenAI API key
# api_key = "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"
# openai.api_key = api_key
#
# # Function to format a datetime object as a string in the desired format
# def format_datetime(dt):
#     # Convert to the desired timezone (e.g., America/Chihuahua)
#     tz = pytz.timezone("America/Chihuahua")
#     dt = dt.astimezone(tz)
#
#     # Get the UTC offset as a string with a colon (":")
#     utc_offset = dt.strftime("%z")
#     formatted_utc_offset = f"{utc_offset[:-2]}:{utc_offset[-2:]}"
#
#     # Format the datetime as a string
#     formatted_datetime = dt.strftime(f"%Y-%m-%dT%H:%M:%S{formatted_utc_offset}")
#     return formatted_datetime
#
# def parse_and_format_datetime(input_text):
#     # Use OpenAI's GPT-3 to parse the date and time
#
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant that extracts date and time."},
#             {"role": "user", "content": f"Extract the date and time from the following text: '{input_text}'."},
#         ],
#     )
#
#     parsed_text = response['choices'][0]['message']['content'].strip()
#
#     try:
#         parsed_datetime = parse(parsed_text, fuzzy=True)
#     except ValueError:
#         parsed_datetime = None
#
#     if parsed_datetime:
#         # Format the parsed datetime as a string in the desired format
#         formatted_datetime = format_datetime(parsed_datetime)
#         return formatted_datetime
#     else:
#         return "Unable to parse the date and time from the input text."
#
# # Example usage:
# input_text = "Tuesday at 10:00 AM"
# formatted_datetime = parse_and_format_datetime(input_text)
# print("Formatted date and time:", formatted_datetime)
import pendulum

def convert_to_iso_string(input_string):
    # Parse the input string to extract the time
    time_str = input_string.split()[-1]

    # Calculate tomorrow's date
    tomorrow = pendulum.now("America/Chihuahua").add(days=1)

    # Combine the date and time components
    datetime_str = f"{tomorrow.format('YYYY-MM-DD')} {time_str}"

    # Parse the combined string into a datetime object
    datetime_obj = pendulum.from_format(datetime_str, 'YYYY-MM-DD hh:mmA', tz="America/Chihuahua")

    # Format the datetime object as an ISO8601 string
    iso_string = datetime_obj.to_iso8601_string()

    return iso_string


# # Test the function with your input string
# input_string = "next tuesday 11:00AM"
# iso_string = convert_to_iso_string(input_string)
# print(iso_string)
