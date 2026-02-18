"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: perceive.py
Description: This defines the "Perceive" module for generative agents. 
"""
import sys
sys.path.append('../../')

from operator import itemgetter
from global_methods import *
from persona.prompt_template.gpt_structure import *
from persona.prompt_template.run_gpt_prompt import *

def generate_poig_score(persona, event_type, description): 
  if "is idle" in description: 
    return 1

  if event_type == "event": 
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat": 
    return run_gpt_prompt_chat_poignancy(persona, 
                           persona.scratch.act_description)[0]

def perceive(persona, maze): 
  """
  Perceives events around the persona and saves it to the memory, both events 
  and spaces. 

  We first perceive the events nearby the persona, as determined by its 
  <vision_r>. If there are a lot of events happening within that radius, we 
  take the <att_bandwidth> of the closest events. Finally, we check whether
  any of them are new, as determined by <retention>. If they are new, then we
  save those and return the <ConceptNode> instances for those events. 

  INPUT: 
    persona: An instance of <Persona> that represents the current persona. 
    maze: An instance of <Maze> that represents the current maze in which the 
          persona is acting in. 
  OUTPUT: 
    ret_events: a list of <ConceptNode> that are perceived and new. 
  """
  # PERCEIVE SPACE
  # We get the nearby tiles given our current tile and the persona's vision
  # radius. 
  nearby_tiles = maze.get_nearby_tiles(persona.scratch.curr_tile, 
                                       persona.scratch.vision_r)

  # We then store the perceived space. Note that the s_mem of the persona is
  # in the form of a tree constructed using dictionaries. 
  for i in nearby_tiles: 
    i = maze.access_tile(i)
    if i["world"]: 
      if (i["world"] not in persona.s_mem.tree): 
        persona.s_mem.tree[i["world"]] = {}
    if i["sector"]: 
      if (i["sector"] not in persona.s_mem.tree[i["world"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]] = {}
    if i["arena"]: 
      if (i["arena"] not in persona.s_mem.tree[i["world"]]
                                              [i["sector"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] = []
    if i["game_object"]: 
      if (i["game_object"] not in persona.s_mem.tree[i["world"]]
                                                    [i["sector"]]
                                                    [i["arena"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] += [
                                                             i["game_object"]]

  # PERCEIVE EVENTS. 
  # We will perceive events that take place in the same arena as the
  # persona's current arena. 
  curr_arena_path = maze.get_tile_path(persona.scratch.curr_tile, "arena")
  # We do not perceive the same event twice (this can happen if an object is
  # extended across multiple tiles).
  percept_events_set = set()
  # We will order our percept based on the distance, with the closest ones
  # getting priorities. 
  percept_events_list = []
  # First, we put all events that are occuring in the nearby tiles into the
  # percept_events_list
  for tile in nearby_tiles: 
    tile_details = maze.access_tile(tile)
    if tile_details["events"]: 
      if maze.get_tile_path(tile, "arena") == curr_arena_path:  
        # This calculates the distance between the persona's current tile, 
        # and the target tile.
        dist = math.dist([tile[0], tile[1]], 
                         [persona.scratch.curr_tile[0], 
                          persona.scratch.curr_tile[1]])
        # Add any relevant events to our temp set/list with the distant info. 
        for event in tile_details["events"]: 
          if event not in percept_events_set: 
            percept_events_list += [[dist, event]]
            percept_events_set.add(event)

  # We sort, and perceive only persona.scratch.att_bandwidth of the closest
  # events. If the bandwidth is larger, then it means the persona can perceive
  # more elements within a small area. 
  percept_events_list = sorted(percept_events_list, key=itemgetter(0))
  perceived_events = []
  for dist, event in percept_events_list[:persona.scratch.att_bandwidth]: 
    perceived_events += [event]

  # Storing events.
  # <ret_events> is a list of <ConceptNode> instances from the persona's
  # associative memory.

  # First pass: collect new events and their embedding texts for batching.
  latest_events = persona.a_mem.get_summarized_latest_events(
                                  persona.scratch.retention)
  new_events = []  # list of (s, p, o, desc, desc_embedding_in, keywords)
  texts_to_embed = []
  text_indices = []  # maps into new_events

  for p_event in perceived_events:
    s, p, o, desc = p_event
    if not p:
      p = "is"
      o = "idle"
      desc = "idle"
    desc = f"{s.split(':')[-1]} is {desc}"
    p_event = (s, p, o)

    if p_event not in latest_events:
      keywords = set()
      sub = p_event[0]
      obj = p_event[2]
      if ":" in p_event[0]:
        sub = p_event[0].split(":")[-1]
      if ":" in p_event[2]:
        obj = p_event[2].split(":")[-1]
      keywords.update([sub, obj])

      desc_embedding_in = desc
      if "(" in desc:
        desc_embedding_in = (desc_embedding_in.split("(")[1]
                                              .split(")")[0]
                                              .strip())

      new_events.append((s, p, o, desc, desc_embedding_in, keywords, p_event))

      # Collect texts that need embedding (not already in a_mem cache)
      if desc_embedding_in not in persona.a_mem.embeddings:
        texts_to_embed.append(desc_embedding_in)
        text_indices.append(len(new_events) - 1)

      # Also check if chat embedding is needed
      if p_event[0] == f"{persona.name}" and p_event[1] == "chat with":
        if persona.scratch.act_description not in persona.a_mem.embeddings:
          texts_to_embed.append(persona.scratch.act_description)
          # We'll handle this separately; just ensure it's batched

  # Batch-fetch all needed embeddings at once
  if texts_to_embed:
    batch_embeddings = get_embeddings_batch(texts_to_embed)
    embed_map = dict(zip(texts_to_embed, batch_embeddings))
  else:
    embed_map = {}

  # Second pass: create memory entries with pre-fetched embeddings
  ret_events = []
  for s, p, o, desc, desc_embedding_in, keywords, p_event in new_events:
    if desc_embedding_in in persona.a_mem.embeddings:
      event_embedding = persona.a_mem.embeddings[desc_embedding_in]
    elif desc_embedding_in in embed_map:
      event_embedding = embed_map[desc_embedding_in]
    else:
      event_embedding = get_embedding(desc_embedding_in)
    event_embedding_pair = (desc_embedding_in, event_embedding)

    event_poignancy = generate_poig_score(persona, "event", desc_embedding_in)

    chat_node_ids = []
    if p_event[0] == f"{persona.name}" and p_event[1] == "chat with":
      curr_event = persona.scratch.act_event
      if persona.scratch.act_description in persona.a_mem.embeddings:
        chat_embedding = persona.a_mem.embeddings[
                           persona.scratch.act_description]
      elif persona.scratch.act_description in embed_map:
        chat_embedding = embed_map[persona.scratch.act_description]
      else:
        chat_embedding = get_embedding(persona.scratch.act_description)
      chat_embedding_pair = (persona.scratch.act_description,
                             chat_embedding)
      chat_poignancy = generate_poig_score(persona, "chat",
                                           persona.scratch.act_description)
      chat_node = persona.a_mem.add_chat(persona.scratch.curr_time, None,
                    curr_event[0], curr_event[1], curr_event[2],
                    persona.scratch.act_description, keywords,
                    chat_poignancy, chat_embedding_pair,
                    persona.scratch.chat)
      chat_node_ids = [chat_node.node_id]

    ret_events += [persona.a_mem.add_event(persona.scratch.curr_time, None,
                         s, p, o, desc, keywords, event_poignancy,
                         event_embedding_pair, chat_node_ids)]
    persona.scratch.importance_trigger_curr -= event_poignancy
    persona.scratch.importance_ele_n += 1

  return ret_events




  











