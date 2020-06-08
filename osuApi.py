import requests
import json
import oppaipy
import random
import os
import pyttanko as osu
import io
import oppadc
import pymongo
import time
import subprocess
import sys
from maniera.calculator import Maniera
from datetime import datetime


cf = os.getcwd()
f = open(f"{cf}/api_keys")
api_keys = f.read().splitlines()
mongo_client = pymongo.MongoClient(host="127.0.0.1", port=int(api_keys[3]))
maps = mongo_client.osu_cache["maps"]
s = requests.Session()
p = osu.parser()

class API:
	def __init__(self, api_key):
		self.api_key = api_key
	
	def get_top(self, user, limit=5, mode = "0"):
		url = "https://osu.ppy.sh/api/get_user_best"
		params = {"k": self.api_key, "u": user, "limit": limit, "m": mode}
		req = s.get(url, params=params)
		req = json.loads(req.content.decode("utf8"))
		return req

	def get_scores(self, user, beatmap_id, mode="0"):
		url = "https://osu.ppy.sh/api/get_scores"
		params = {"k": self.api_key, "u": user, "b": beatmap_id, "m": mode}
		req = s.get(url, params=params)
		req = json.loads(req.content.decode("utf8"))
		print(req)
		return req
		
	def get_recent(self, user, mode="0"):
		url = "https://osu.ppy.sh/api/get_user_recent"
		params = {"k": self.api_key, "u": user, "m": mode}
		print(params, "params")
		req = s.get(url, params=params)
		req = json.loads(req.content.decode("utf8"))
		print(req, "req")
		return req

	def get_beatmap(self, beatmap_id, mods):
		url = "https://osu.ppy.sh/api/get_beatmaps"
		if mods:
			url = f"https://osu.ppy.sh/api/get_beatmaps?mods={mods}"
		params = {"k": self.api_key, "b": beatmap_id}
		req = s.get(url, params=params)
		req = json.loads(req.content.decode("utf8"))
		return req

	def count_acc(self, count50, count100, count300, countmiss):
		up50 = count50 * 50; up100 = count100 * 100; up300 = count300 * 300
		acc = (up50+ up100+ up300)/(300*(count50+count100+count300+countmiss))
		return float(acc)


	def count_pp(self, mods=0, acc=0, combo=0, misses=0, beatmap_id=0, mode = "0", scores = [0]):
		start = time.time()
		data = None
		pp_list = {}
		if maps.count() == 0:
			data = s.get(f"https://osu.ppy.sh/osu/{beatmap_id}").content.decode("utf8")
			maps.insert_one({str(beatmap_id): data})
		else:
			for x in maps.find():
				key = list(x.keys())[1]
				if str(key) == beatmap_id:
					data = x[beatmap_id]
					break
			if not data:
				data = s.get(f"https://osu.ppy.sh/osu/{beatmap_id}").content.decode("utf8")
				maps.insert_one({str(beatmap_id): data})
		if mode == "0":
			calc = oppaipy.Calculator(beatmap_data = data)
			#print(data)
			if combo:
				calc.set_combo(combo); calc.set_misses(misses); calc.set_mods(mods); calc.set_accuracy_percent(acc[0])
				calc.calculate()
				PP = calc.pp
				pp_list["play_pp"] = PP

			for a in acc:	
				calc.reset()
				calc.set_mods(mods); calc.set_accuracy_percent(a)
				calc.calculate(); maxPP = calc.pp
				pp_list[f"maxPP_{a}"] = maxPP 
			print(pp_list, "!!!")
			end = time.time()
			print("TIME:", end-start)
			return pp_list
		elif mode == "3":
			for score in scores:
				calc = Maniera(osupath=data, mods=mods, score=score)
				calc.calculate()
				pp_list[f"play_pp_{score}"] = (round(calc.pp, 2), calc.note_count) 
			print(pp_list)
			return pp_list

	def get_diff(self, beatmap_id, mods, mode = "0"):
		start = time.time()
		data = None
		if maps.count() == 0:
			data = s.get(f"https://osu.ppy.sh/osu/{beatmap_id}").content.decode("utf8")
			maps.insert_one({str(beatmap_id): data})
		else:
			for x in maps.find():
				key = list(x.keys())[1]
				print(key)
				if str(key) == beatmap_id:
					print("here")
					data = x[beatmap_id]
					break
			if not data:
				data = s.get(f"https://osu.ppy.sh/osu/{beatmap_id}").content.decode("utf8")
				maps.insert_one({str(beatmap_id): data})
		if mode == "0":
			Map = oppadc.OsuMap(raw_str=data)
			if mods:
				diff = Map.getDifficulty(mods.upper())
			else:
				diff = Map.getDifficulty(None)
		elif mode == "3":
			calc = Maniera(data, mods, 0)
			calc.calculate()
			diff = {"od": calc.od}
		end = time.time()
		print("TIME:", end-start)
		return(diff)

	def get_user(self, user_id):
		url = "https://osu.ppy.sh/api/get_user"
		params = {"k": self.api_key, "u": user_id}
		req = s.get(url, params=params)
		req = json.loads(req.content.decode("utf8"))
		return req

	def force_update_database(self, beatmap_id):
		url = f"https://osu.ppy.sh/osu/{beatmap_id}"
		data = s.get(url).content.decode("utf-8")
		if maps.count == 0:
			maps.insert_one({str(beatmap_id): data})
		else:
			for x in maps.find({}):
				_id = x["_id"]
				res = maps.find_one_and_replace({str(beatmap_id): {'$regex': '.*.*'}}, {str(beatmap_id): data})
				if not res:
					maps.insert_one({str(beatmap_id): data})
		print(beatmap_id, "done")
		time.sleep(0.1)

