import flask
from flask import request, jsonify
from collections import Counter
from typing import Tuple, Container

import en_core_web_sm


app = flask.Flask(__name__)
app.config["DEBUG"] = True

nlp = en_core_web_sm.load()
IGNORE_PIPES = [pipe for pipe in nlp.pipe_names if pipe not in {"ner"}]
nlp.disable_pipes(*IGNORE_PIPES)

# NLP constants
SMS_WORDS = frozenset(
    {
        "stop", "help"}
)
DEFAULT_BRAND_LABELS = frozenset({"ORG"})
DEFAULT_REPLACEMENT_LABELS = frozenset({"DATE", "TIME"})

def is_ascii(text: str) -> bool:
    if all(ord(c) < 255 for c in text):
        return True
    else:
        return False

def count_named_entities(content: str, min_word_len: int = 3, max_word_len: int = 40,
                         brand_labels: Container[str] = DEFAULT_BRAND_LABELS,
                         replacement_labels: Container[str] = DEFAULT_REPLACEMENT_LABELS) -> Tuple[Counter, Counter]:
    brands = []
    words = []
    if content:
        nlp_content = nlp(content)
        for word in nlp_content.ents:
            # Extract brands and add to brands list
            if all([
                (word.label_ in brand_labels), (min_word_len <= len(word.text) <= max_word_len),
                is_ascii(word.text), (word.lower_ not in SMS_WORDS)
            ]):
                vcb_word = nlp.vocab[word.text]
                if not (vcb_word.like_url or vcb_word.like_email):
                    brands.append(word.text)
            if word.label_ in replacement_labels:
                words.append(word.label_)

        for word in nlp_content:
            if all([
                min_word_len <= len(word) <= max_word_len,
                not any([word.is_stop, word.is_punct, word.like_num, word.is_space,
                         (word.ent_type_ in replacement_labels), (word.lower_ in SMS_WORDS)])
            ]):
                # Extract word categories if in our list or lemmatized words
                if word.like_email:
                    words.append("EMAIL")
                elif word.like_url:
                    words.append("URL")
                elif is_ascii(word.text):
                    words.append(word.lemma_.lower())

    return Counter(brands), Counter(words)

@app.route('/endpoint/alpha/', methods=['POST'])
def api_endpointA():
    if request.is_json:
        content = request.get_json()
        inputmsg = content["inputmsg"]
        brands, words = count_named_entities(inputmsg)
    return '{}\n{}'.format(brands, words)

@app.route('/endpoint/bravo/', methods=['POST'])
def api_endpointB():
    response = dict()
    if request.is_json:
        content = request.get_json()
        inputmsg = content["inputmsg"]
        brands, words = count_named_entities(inputmsg)
        response['entities'] = brands
        response['words'] = words
    return jsonify(response)

app.run()