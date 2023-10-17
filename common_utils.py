def estimate_speech_duration(sentence, words_per_minute=150):
    # Split the sentence into words
    words = sentence.split()

    # Calculate the number of words in the sentence
    num_words = len(words)

    # Calculate the estimated duration in seconds
    duration_seconds = num_words / words_per_minute * 60

    return duration_seconds
