"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: gpt_structure.py
Description: Wrapper functions for calling OpenAI APIs.
"""
import json
import random
import openai
import openai.error
import time
from functools import lru_cache

from utils import *

openai.api_key = openai_api_key

def temp_sleep(seconds=0.1):
  pass  # レート制限は_api_call_with_backoffで対応


def _api_call_with_backoff(func, *args, max_retries=3, **kwargs):
  """APIコールを指数バックオフ付きでリトライする。"""
  for attempt in range(max_retries):
    try:
      return func(*args, **kwargs)
    except openai.error.RateLimitError:
      if attempt < max_retries - 1:
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
      else:
        raise
    except (openai.error.AuthenticationError,
            openai.error.InvalidRequestError):
      raise
    except Exception:
      if attempt < max_retries - 1:
        time.sleep(2 ** attempt)
      else:
        raise

def ChatGPT_single_request(prompt):
  temp_sleep()

  completion = _api_call_with_backoff(
    openai.ChatCompletion.create,
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
  )
  return completion["choices"][0]["message"]["content"]


# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  temp_sleep()

  try:
    completion = _api_call_with_backoff(
    openai.ChatCompletion.create,
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}]
    )
    return completion["choices"][0]["message"]["content"]

  except:
    print ("ChatGPT ERROR")
    return "ChatGPT ERROR"


def ChatGPT_request(prompt): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  # temp_sleep()
  try:
    completion = _api_call_with_backoff(
    openai.ChatCompletion.create,
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
    )
    return completion["choices"][0]["message"]["content"]

  except:
    print ("ChatGPT ERROR")
    return "ChatGPT ERROR"


def _extract_output(gpt_response):
  """Extract the output value from a GPT response.
  Tries JSON parsing first, falls back to raw response."""
  resp = gpt_response.strip()
  # Try JSON extraction first
  end_index = resp.rfind('}') + 1
  if end_index > 0:
    try:
      return json.loads(resp[:end_index])["output"]
    except (json.JSONDecodeError, KeyError):
      pass
  # Fallback: use the raw response as-is
  return resp


def GPT4_safe_generate_response(prompt,
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
  prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose:
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat):

    try:
      curr_gpt_response = GPT4_request(prompt).strip()
      curr_gpt_response = _extract_output(curr_gpt_response)

      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)

      if verbose:
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except:
      pass

  return False


def ChatGPT_safe_generate_response(prompt,
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
  # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt = '"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose:
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat):

    try:
      curr_gpt_response = ChatGPT_request(prompt).strip()
      curr_gpt_response = _extract_output(curr_gpt_response)

      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)

      if verbose:
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except:
      pass

  return False


def ChatGPT_safe_generate_response_OLD(prompt, 
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 
    try: 
      curr_gpt_response = ChatGPT_request(prompt).strip()
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      if verbose: 
        print (f"---- repeat count: {i}")
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass
  print ("FAIL SAFE TRIGGERED") 
  return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response.
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of
                   the parameter and the values indicating the parameter
                   values.
  RETURNS:
    a str of GPT-3's response.
  """
  temp_sleep()
  try:
    response = _api_call_with_backoff(
                openai.ChatCompletion.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=gpt_parameter["temperature"],
                max_tokens=gpt_parameter["max_tokens"],
                top_p=gpt_parameter["top_p"],
                frequency_penalty=gpt_parameter["frequency_penalty"],
                presence_penalty=gpt_parameter["presence_penalty"],
                stream=gpt_parameter["stream"],
                stop=gpt_parameter["stop"],)
    return response.choices[0].message.content
  except:
    print ("TOKEN LIMIT EXCEEDED")
    return "TOKEN LIMIT EXCEEDED"


def generate_prompt(curr_input, prompt_lib_file): 
  """
  Takes in the current input (e.g. comment that you want to classifiy) and 
  the path to a prompt file. The prompt file contains the raw str prompt that
  will be used, which contains the following substr: !<INPUT>! -- this 
  function replaces this substr with the actual curr_input to produce the 
  final promopt that will be sent to the GPT3 server. 
  ARGS:
    curr_input: the input we want to feed in (IF THERE ARE MORE THAN ONE
                INPUT, THIS CAN BE A LIST.)
    prompt_lib_file: the path to the promopt file. 
  RETURNS: 
    a str prompt that will be sent to OpenAI's GPT server.  
  """
  if type(curr_input) == type("string"): 
    curr_input = [curr_input]
  curr_input = [str(i) for i in curr_input]

  f = open(prompt_lib_file, "r")
  prompt = f.read()
  f.close()
  for count, i in enumerate(curr_input):   
    prompt = prompt.replace(f"!<INPUT {count}>!", i)
  if "<commentblockmarker>###</commentblockmarker>" in prompt: 
    prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
  return prompt.strip()


def safe_generate_response(prompt, 
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False): 
  if verbose: 
    print (prompt)

  for i in range(repeat): 
    curr_gpt_response = GPT_request(prompt, gpt_parameter)
    if func_validate(curr_gpt_response, prompt=prompt): 
      return func_clean_up(curr_gpt_response, prompt=prompt)
    if verbose: 
      print ("---- repeat count: ", i, curr_gpt_response)
      print (curr_gpt_response)
      print ("~~~~")
  return fail_safe_response


_EMBEDDING_DICT_CACHE = {}


def get_embedding(text, model="text-embedding-3-small"):
  text = text.replace("\n", " ")
  if not text:
    text = "this is blank"
  emb = _get_embedding_cached(text, model)
  # Also populate the dict cache used by get_embeddings_batch
  _EMBEDDING_DICT_CACHE[(text, model)] = emb
  return emb


@lru_cache(maxsize=4096)
def _get_embedding_cached(text, model):
  response = _api_call_with_backoff(
      openai.Embedding.create, input=[text], model=model)
  return tuple(response['data'][0]['embedding'])


def get_embeddings_batch(texts, model="text-embedding-3-small"):
  """Get embeddings for multiple texts in a single API call.

  Uses a dict cache (_EMBEDDING_DICT_CACHE) shared with the lru_cache.
  Cached texts are returned immediately; uncached texts are batched into
  a single openai.Embedding.create call.

  INPUT:
    texts: list of strings to embed
    model: embedding model name
  OUTPUT:
    list of embedding tuples, same order as input texts
  """
  if not texts:
    return []

  cleaned = [t.replace("\n", " ") or "this is blank" for t in texts]

  # Separate cached from uncached
  results = {}
  uncached = []
  uncached_indices = []
  for i, text in enumerate(cleaned):
    cache_key = (text, model)
    if cache_key in _EMBEDDING_DICT_CACHE:
      results[i] = _EMBEDDING_DICT_CACHE[cache_key]
    else:
      uncached.append(text)
      uncached_indices.append(i)

  # Single batch API call for all uncached texts
  if uncached:
    response = _api_call_with_backoff(
        openai.Embedding.create, input=uncached, model=model)
    for j, item in enumerate(response['data']):
      emb = tuple(item['embedding'])
      idx = uncached_indices[j]
      results[idx] = emb
      # Store in dict cache for future batch calls
      _EMBEDDING_DICT_CACHE[(uncached[j], model)] = emb

  return [results[i] for i in range(len(texts))]


if __name__ == '__main__':
  gpt_parameter = {"engine": "gpt-4o-mini", "max_tokens": 50,
                   "temperature": 0, "top_p": 1, "stream": False,
                   "frequency_penalty": 0, "presence_penalty": 0,
                   "stop": ['"']}
  curr_input = ["driving to a friend's house"]
  prompt_lib_file = "prompt_template/test_prompt_July5.txt"
  prompt = generate_prompt(curr_input, prompt_lib_file)

  def __func_validate(gpt_response): 
    if len(gpt_response.strip()) <= 1:
      return False
    if len(gpt_response.strip().split(" ")) > 1: 
      return False
    return True
  def __func_clean_up(gpt_response):
    cleaned_response = gpt_response.strip()
    return cleaned_response

  output = safe_generate_response(prompt, 
                                 gpt_parameter,
                                 5,
                                 "rest",
                                 __func_validate,
                                 __func_clean_up,
                                 True)

  print (output)




















