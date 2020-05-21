import discord
import osuApi
import re
import binascii
import os
from io import StringIO, BytesIO
from pippy.parser.beatmap import Beatmap
from pippy.pp.counter import calculate_pp, Mods, calculate_pp_by_acc
from pippy import diff
from enum import Enum
import pymongo
import sys
import traceback
import math
import time
from datetime import datetime


def r(x):
	return round(x, 2)

cf = os.getcwd()
f = open(f"{cf}/api_keys")
api_keys = f.read().splitlines()
api = osuApi.API(api_keys[0])

mongo_client = pymongo.MongoClient(host="127.0.0.1", port=int(api_keys[3]))
users = mongo_client.osu_db["users"]

def recent(user, channel, dc_user):
	try:
		best = False
		try:
			if "-p" in user:
				pos = user.index("-p")
				playNum = int(user[pos+1])
				showNum = playNum
				del user[user.index("-p"):user.index("-p") + 1]
			else:
				playNum = 0
				showNum = playNum + 1
			if "-b" in user:
				best = True
				del user[user.index("-b")]
		except:
			playNum = 0
			showNum = playNum + 1
			pass
		if len(user) == 1:
			for x in users.find({}, {"_id":0}):
				key = list(x.keys())[0]
				if str(dc_user.author) == str(key):
					user.append(list(x.values())[0])


		res = api.get_recent(user[1])
		if True:
			pp_list = []
			for p in res:
				activeMods = num_to_mod(int(p["enabled_mods"]))

				if "NOMOD" not in activeMods:
					mods_upper = ''.join(activeMods)
				else:
					mods_upper = None

				if mods_upper:
					mod_number = mod_to_num(mods_upper)
				else:
					mod_number = 0

				acc, accn = get_acc(p["count50"], p["count100"], p["count300"], p["countmiss"])

				pp_max = api.count_pp(mod_number, [float(acc)], int(p["maxcombo"]), int(p["countmiss"]), p["beatmap_id"])
				pp_list.append(pp_max["play_pp"])
			play = res[pp_list.index(max(pp_list))]
			showNum = pp_list.index(max(pp_list))
		else:
			play = res[playNum]
		user_info = api.get_user(play['user_id'])[0]
		activeMods = num_to_mod(int(play["enabled_mods"]))

		beatmap_id = play['beatmap_id']
		beatmap = get_beatmap_mods(activeMods, beatmap_id)
		beatmapset_id = beatmap["beatmapset_id"]

		acc, accn = get_acc(play["count50"], play["count100"], play["count300"], play["countmiss"])

		if "NOMOD" not in activeMods:
			mods_upper = ''.join(activeMods)
		else:
			mods_upper = None

		if mods_upper:
			mod_number = mod_to_num(mods_upper)
		else:
			mod_number = 0
		pp_s = api.count_pp(mod_number, [float(acc)], int(play["maxcombo"]), int(play["countmiss"]), beatmap_id)

		msg = ""

		msg += f"""```Title: {beatmap["title"]} + {mods_upper} [{beatmap["version"]}⭐{round(float(beatmap['difficultyrating']), 2)}]\n"""
		msg += f"""Mapper: {beatmap["creator"]}\n"""
		if int(pp_s["play_pp"] > int(pp_s[f"maxPP_{acc}"])):
			msg += f"""Score: {play['score']} Combo: {play['maxcombo']}/{beatmap["max_combo"]} {round(pp_s["play_pp"], 2)}pp)\n"""
		else:
			msg += f"""Score: {play['score']} Combo: {play['maxcombo']}/{beatmap["max_combo"]} {round(pp_s["play_pp"], 2)}pp ({round(pp_s[f"maxPP_{acc}"], 2)}pp for {round(acc, 2)}% FC)\n"""
		msg += f"""Rank: {play['rank']} {round(acc, 2)}% [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]```"""

		profile_url = 'https://a.ppy.sh/{}'.format(play['user_id'])
		title = f"Most recent Osu std play for {user_info['username']}"
		map_image_url = f"https://b.ppy.sh/thumb/{beatmapset_id}.jpg"

		em = discord.Embed(description='', colour=discord.Color(0))
		em.set_footer(text=f"Recent #{showNum}")
		em.set_author(name=title, icon_url=profile_url, url=f"""https://osu.ppy.sh/beatmapsets/{beatmapset_id}#osu/{beatmap_id}""")
		em.set_thumbnail(url=map_image_url)
		em.description = msg

		set_last_map(dc_user, beatmap_id)
		return em
	except:
		e = sys.exc_info()[0]
		e_tr = traceback.format_exc()
		if e == IndexError:
			print("no user specified")
			em = discord.Embed(description="No plays made or user doesn't exist")
		elif e == ValueError:
			print(e_tr)
			em = discord.Embed(description="name dont exist or smth")
		else:
			print(e_tr)
			em = discord.Embed(description=f"XD error")
		return em

def compare(user, beatmap_id, dc_user):
	try:
		if len(user) == 1:
			for x in users.find({}, {"_id":0}):
				key = list(x.keys())[0]
				print(key)
				print(dc_user.author)
				if str(dc_user.author) == str(key):
					user.append(list(x.values())[0])
			user = user[1]
	except IndexError as e:
		em = discord.Embed(description="^setuser to set user")
		return(em)

	msg = ""
	try:

		scores = api.get_scores(user, beatmap_id)
		player = api.get_user(user)[0]

		if len(scores) == 0:
			em = discord.Embed(description="you dont set score nooob")
			return em
		
		for score in scores:

			activeMods = num_to_mod(score["enabled_mods"])
			conc_mods = "".join(activeMods)
			beatmap = get_beatmap_mods(activeMods, beatmap_id)
			acc, accn = get_acc(score["count50"], score["count100"], score["count300"], score["countmiss"])
			mod_number = mod_to_num(conc_mods.upper())
			pp_for_fc = api.count_pp(mod_number, [acc], None, None, beatmap_id)
			

			msg += f"```{scores.index(score) + 1}. {conc_mods}\n"
			msg += f"""Title: {beatmap["title"]} [{beatmap["version"]} ⭐{round(float(beatmap["difficultyrating"]), 2)}]\n"""
			if int(score["maxcombo"]) == int(beatmap["max_combo"]):
				msg += f"""{score["rank"]} {round(acc, 2)}% {round(float(score["pp"]), 3)}pp [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]\n"""
			elif float(score["pp"]) > float(pp_for_fc[f"maxPP_{acc}"]):
				msg += f"""{score["rank"]} {round(acc, 2)}% {round(float(score["pp"]), 3)}pp [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]\n"""				
			else:
				msg += f"""{score["rank"]} {round(acc, 2)}% {round(float(score["pp"]), 3)}pp ({round(pp_for_fc[f"maxPP_{acc}"], 2)}pp for {round(acc, 2)}% FC) [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]\n"""				
			msg += f"""Score:{score["score"]}, {score["maxcombo"]}x/{beatmap["max_combo"]}x```"""
			msg += "\n"
			
			profile_url = 'https://a.ppy.sh/{}'.format(player['user_id'])
			title = f"""Top osu plays in {beatmap["title"]} for {score['username']}"""
			map_image_url = f"""https://b.ppy.sh/thumb/{beatmap["beatmapset_id"]}.jpg"""
			em = discord.Embed(description='', colour=discord.Color(0))
			em.set_author(name=title, icon_url=profile_url, url = f"""https://osu.ppy.sh/beatmapsets/{beatmap["beatmapset_id"]}#osu/{beatmap_id}""")
			em.set_thumbnail(url=map_image_url)
			em.description = msg
	except:
		e = sys.exc_info()[0]
		e_tr = traceback.format_exc()
		print(e)
		if e == IndexError:
			em = discord.Embed(description="no score")
		else:
			print(e_tr)
			em = discord.Embed(description=f"idk men")
		return em

	return em

def user_top_10(command, dc_user, limit=5):
	pp_time = {}
	try:
		recent = False
		if "-p" in command:
			pos = command.index("-p")
			playNum=int(command[pos + 1])
			del command[pos + 1]
			del command[pos]
		if "-r" in command:
			pos = command.index("-r")
			playNum = None
			recent=True
			del command[pos]
		else:
			playNum = None
			
	except:
		e_tr = traceback.format_exc()
		print(e_tr)
		playNum = None
		limit=5
		pass
	try:
		if len(command) == 1:
			for x in users.find({}, {"_id":0}):
				key = list(x.keys())[0]
				print(key)
				print(dc_user.author)
				if str(dc_user.author) == str(key):
					command.append(list(x.values())[0])
	except IndexError:
		em = discord.Embed(description="no user set")
		return(em)
	try: 
		if playNum and not recent:
			scores = api.get_top(command[1], limit=100)
			score = scores[playNum - 1]
			scores = []
			scores.append(score)
			set_last_map(dc_user, score["beatmap_id"])	
		else:
			scores = api.get_top(command[1])
		if recent:
			scores = []
			scores_recent = api.get_top(command[1], limit=100)
			print(scores_recent)
			for score in scores_recent:
				fixeddate = datetime.strptime(score["date"], "%Y-%m-%d %H:%M:%S")
				date_seconds = fixeddate.timestamp()
				pp_time.update({date_seconds: score["pp"]})

			for i in sorted(pp_time, reverse=True)[:5]:
				for score in scores_recent:
					if pp_time[i] == score["pp"]:
						scores.append(score)
						print("top")
				print(i, pp_time[i])
		msg = ""
		em = discord.Embed(description='', colour=discord.Color(0))
		for score in scores:
			beatmap_id = score["beatmap_id"]
			activeMods = num_to_mod(score["enabled_mods"])
			conc_mods = "".join(activeMods)
			beatmap = get_beatmap_mods(activeMods, beatmap_id)
			acc, accn = get_acc(score["count50"], score["count100"], score["count300"], score["countmiss"])
			mod_number = mod_to_num(conc_mods.upper())
			pp_for_fc = api.count_pp(mod_number, [acc], None, None, beatmap_id)

			msg += f"```{scores.index(score) + 1}. {conc_mods}\n"
			msg += f"""Title: {beatmap["title"]} [{beatmap["version"]} ⭐{round(float(beatmap["difficultyrating"]), 2)}]\n"""
			if int(score["maxcombo"]) == int(beatmap["max_combo"]):
				msg += f"""{score["rank"]} {round(acc, 2)}% {round(float(score["pp"]), 3)}pp [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]\n"""
			else:
				msg += f"""{score["rank"]} {round(acc, 2)}% {round(float(score["pp"]), 3)}pp ({round(pp_for_fc[f"maxPP_{acc}"], 2)}pp for {round(acc, 2)}% FC) [{accn[2]}/{accn[1]}/{accn[0]}/{accn[3]}]\n"""				
			msg += f"""Score:{score["score"]}, {score["maxcombo"]}x/{beatmap["max_combo"]}x```"""
			msg += "\n"
			
		
		title = f"""Top osu plays for {command[1]}"""
		profile_url = 'https://a.ppy.sh/{}'.format(score['user_id'])
		if playNum:
			map_image_url = f"""https://b.ppy.sh/thumb/{beatmap["beatmapset_id"]}.jpg"""
			em.set_author(name=title, icon_url=profile_url, url = f"""https://osu.ppy.sh/beatmapsets/{beatmap["beatmapset_id"]}#osu/{beatmap_id}""")
			em.set_thumbnail(url=map_image_url)
		else:
			em.set_author(name=title, icon_url=profile_url, url = f"""https://osu.ppy.sh/users/{score["user_id"]}/osu""")
		em.description = msg
	except:
		e_tr = traceback.format_exc()
		print(e_tr)
		em = discord.Embed(description=f"eror")
		return em
	return em

def map_info(command, beatmap_id):
	time_module = time.time()
	try:
		if "-a" in command:
			pos = command.index("-a")
			try:
				acc = float(command[pos + 1])
				del command[pos + 1]
				del command[pos]
			except:
				acc = None
				pass
		else:
			acc = None
			pass
		try:	
			if command[1]:
				print(command, "here")
				mods = command[1].upper()
				mod_number = mod_to_num(mods)
				beatmap = get_beatmap_mods(mods, beatmap_id)
			else:
				mods = None
				mod_number = 0
				beatmap = api.get_beatmap(beatmap_id, mods)[0]
		except:
			mods = None
			mod_number = 0
			beatmap = api.get_beatmap(beatmap_id, mods)[0]

		accs=[95.0, 99.0, 100.0]
		pp_for_accs = api.count_pp(mod_number, accs, None, None, beatmap_id)

		if mods:
			diff = api.get_diff(beatmap_id, mods.upper())
		else:
			diff = api.get_diff(beatmap_id, None)
		if acc and acc > 0 and acc <= 100:
			pp_for_acc = api.count_pp(mod_number, [float(acc)], None, None, beatmap_id)
		msg = ''
		if diff.od > 10.0:
			od = 10.0
		else:
			od = diff.od
		msg += f"""```[{beatmap["version"]} ⭐{round(float(beatmap["difficultyrating"]), 2)}]\n"""
		if mods:
			if "DT" in mods:
				msg += f"""Mods:{mods} Max combo: {beatmap["max_combo"]} BPM:{math.trunc(float(beatmap["bpm"]) * 1.5)}\n"""
			else:
				msg += f"""Mods:{mods} Max combo: {beatmap["max_combo"]} BPM:{math.trunc(float(beatmap["bpm"]))}\n"""
		else:
			msg += f"""Mods: -- Max combo: {beatmap["max_combo"]} BPM:{beatmap["bpm"]}\n"""
		msg += f"""CS:{r(diff.cs)} OD:{r(od)} AR:{r(diff.ar)} HP:{r(diff.hp)}\n"""
		if acc and acc > 0 and acc <= 100:
			msg += f"""pp: {acc}%-{round(float(pp_for_acc[f"maxPP_{acc}"]), 2)} 99%-{round(float(pp_for_accs["maxPP_99.0"]), 2)} 100%:-{round(float(pp_for_accs["maxPP_100.0"]), 2)}```"""
		else:
			msg += f'pp: 95%-{round(float(pp_for_accs["maxPP_95.0"]), 2)} 99%-{round(float(pp_for_accs["maxPP_99.0"]), 2)} 100%-{round(float(pp_for_accs["maxPP_100.0"]), 2)}```'

		title = f"""Map info for {beatmap["title"]}"""
		map_image_url = f"""https://b.ppy.sh/thumb/{beatmap["beatmapset_id"]}.jpg"""
		em = discord.Embed(description='', colour=discord.Color(0))
		em.set_author(name=title, url=f"""https://osu.ppy.sh/beatmapsets/{beatmap["beatmapset_id"]}#osu/{beatmap_id}""")
		em.set_thumbnail(url=map_image_url)
		
		em.description = msg
		time_taken = time.time() - time_module
		em.set_footer(text=str(time_taken))
	except:
		e = traceback.format_exc()
		print(e)
		em = discord.Embed(description=f"eror")
		return em
	return em

def get_acc(n50, n100, n300, nMiss):
	
	accn = [n50, n100, n300, nMiss]
	for i in range(0, len(accn)):
		accn[i] = int(accn[i])
	acc = api.count_acc(
		accn[0], accn[1], accn[2], accn[3]) * 100
	return acc, accn

def get_beatmap_mods(mods, beatmap_id):
		if "DT" in mods and "HR" not in mods:
			beatmap = api.get_beatmap(beatmap_id, 64); return beatmap[0]
		if "HR" in mods and "DT" not in mods:
			beatmap = api.get_beatmap(beatmap_id, 16); return beatmap[0]
		if "HR" and "DT" in mods:
			beatmap = api.get_beatmap(beatmap_id, 80); return beatmap[0]
		else:
			beatmap = api.get_beatmap(beatmap_id, None); return beatmap[0]


def set_last_map(dc_user, beatmap_id):
	last_map = mongo_client.osu_db["last_map"]
	if last_map.estimated_document_count == 0:
		last_map.insert_one({str(dc_user.channel.id): beatmap_id})	
	else:
		for x in last_map.find({}):
			_id = x["_id"]
			res = last_map.find_one_and_replace({str(dc_user.channel.id): {'$regex': '.*.*'}}, {str(dc_user.channel.id): beatmap_id})
			print(res)
			if res == None:
				last_map.insert_one({str(dc_user.channel.id): beatmap_id})

def add_user(name, discord_name):
	users = mongo_client.osu_db["users"]

	for x in users.find({}, {"_id": 0}):
		key = list(x.keys())[0]
		value = list(x.values())[0]
		print(key, value, "add_user")
		if str(discord_name) == str(key):
			users.find_one_and_replace({str(discord_name): str(value)}, {str(discord_name): str(name)})
			return

	users.insert_one({f"{discord_name}": f"{name}"})

def remove_user(name, discord_name):

	users = mongo_client.osu_db["users"]
	users.delete_one({f"{discord_name}": f"{name}"})


def num_to_mod(number):
	"""This is the way pyttanko does it. 
	Just as an actual bitwise instead of list. 
	Deal with it."""
	number = int(number)
	mod_list = []

	if number & 1 << 0:
		mod_list.append('NF')
	if number & 1 << 1:
		mod_list.append('EZ')
	if number & 1 << 3:
		mod_list.append('HD')
	if number & 1 << 4:
		mod_list.append('HR')
	if number & 1 << 5:
		mod_list.append('SD')
	if number & 1 << 9:
		mod_list.append('NC')
	elif number & 1 << 6:
		mod_list.append('DT')
	if number & 1 << 7:
		mod_list.append('RX')
	if number & 1 << 8:
		mod_list.append('HT')
	if number & 1 << 10:
		mod_list.append('FL')
	if number & 1 << 12:
		mod_list.append('SO')
	if number & 1 << 15:
		mod_list.append('4 KEY')
	if number & 1 << 16:
		mod_list.append('5 KEY')
	if number & 1 << 17:
		mod_list.append('6 KEY')
	if number & 1 << 18:
		mod_list.append('7 KEY')
	if number & 1 << 19:
		mod_list.append('8 KEY')
	if number & 1 << 20:
		mod_list.append('FI')
	if number & 1 << 24:
		mod_list.append('9 KEY')
	if number & 1 << 25:
		mod_list.append('10 KEY')
	if number & 1 << 26:
		mod_list.append('1 KEY')
	if number & 1 << 27:
		mod_list.append('3 KEY')
	if number & 1 << 28:
		mod_list.append('2 KEY')
	if not mod_list:
		mod_list.append("NOMOD")
	return mod_list


def mod_to_num(mods: str):
	"""It works."""
	mods = mods.upper()
	total = 0

	if 'NF' in mods:
		total += 1 << 0
	if 'EZ' in mods:
		total += 1 << 1
	if 'HD' in mods:
		total += 1 << 3
	if 'HR' in mods:
		total += 1 << 4
	if 'SD' in mods:
		total += 1 << 5
	if 'DT' in mods:
		total += 1 << 6
	if 'RX' in mods:
		total += 1 << 7
	if 'HT' in mods:
		total += 1 << 8
	if 'NC' in mods:
		total += 1 << 9
	if 'FL' in mods:
		total += 1 << 10
	if 'SO' in mods:
		total += 1 << 12
	if 'PF' in mods:
		total += 1 << 14
	if '4 KEY' in mods:
		total += 1 << 15
	if '5 KEY' in mods:
		total += 1 << 16
	if '6 KEY' in mods:
		total += 1 << 17
	if '7 KEY' in mods:
		total += 1 << 18
	if '8 KEY' in mods:
		total += 1 << 19
	if 'FI' in mods:
		total += 1 << 20
	if '9 KEY' in mods:
		total += 1 << 24
	if '10 KEY'in mods:
		total += 1 << 25
	if '1 KEY' in mods:
		total += 1 << 26
	if '3 KEY' in mods:
		total += 1 << 27
	if '2 KEY' in mods:
		total += 1 << 28

	return int(total)


class bot(discord.Client):
	async def on_ready(self):
		print(self.user)
		print(self.latency * 1000, "ms")

	async def on_message(self, message):
		if message.author == client.user:
			return
		command = message.content.split(" ")
		print(command)
		msgChannel = message.channel
		if command[0] == "^teme":
			await msgChannel.send(file=discord.File(f'{cf}/meems/temehd_2.png'))
		elif command[0] == "^bing":
			await msgChannel.send(file=discord.File(f'{cf}/meems/bing.mp4'))
		elif command[0] == '^pumppu':
			await msgChannel.send(file=discord.File(f"{cf}/meems/dodedoaodaoe.mp4"))
		elif command[0] == '^sipa':
			await msgChannel.send(file=discord.File(f"{cf}/meems/Screenshot_20191023-000929_Instagram.png"))
		elif command[0] == '^kurwamamut':
			await msgChannel.send(file=discord.File(f"{cf}/meems/KURWA_MAMUT_1_1.mp3"))
		elif command[0] == "^grr":
			await msgChannel.send(file=discord.File(f"{cf}/meems/moka.webm"))
		elif command[0] == "^rs" or command[0] == "^recent":
			msgSend = recent(command, msgChannel, message)
			try:
				await msgChannel.send(embed=msgSend)
			except discord.HTTPException as e:
				print("no message?", e)
				pass
		elif command[0] == "^c":
			last_map = mongo_client.osu_db["last_map"]
			for x in last_map.find({}, {"_id": 0}):
				key = list(x.keys())[0]
				value = list(x.values())[0]
				print(key, "value", str(message.channel.id))
				if str(message.channel.id) == str(key):
					print("hererer")
					msgSend = compare(command, value, message)
					print(msgSend)
					break
			try:
				await msgChannel.send(embed=msgSend)
			except discord.HTTPException as e:
				await msgChannel.send("No scores")
		elif command[0] == "^m":
			last_map = mongo_client.osu_db["last_map"]
			for x in last_map.find({}, {"_id": 0}):
				key = list(x.keys())[0]
				value = list(x.values())[0]
				print(key, "value", str(message.channel.id))
				if str(message.channel.id) == str(key):
					#print("hererer")
					msgSend = map_info(command, value)
					print(msgSend)
					break
			try:
				await msgChannel.send(embed=msgSend)
			except discord.HTTPException as e:
				await msgChannel.send("No scores")
		elif command[0] == "^top":
			msgSend = user_top_10(command, message)
			try:
				await msgChannel.send(embed=msgSend)
			except discord.HTTPException as e:
				await(msgChannel.send("no scores"))
		elif command[0] == "^setuser":
			add_user(command[1], message.author)
			await msgChannel.send(f"set your profile to {command[1]}")
			return
		elif command[0] == "^remuser":
			remove_user(command[1], message.author)
			await msgChannel.send(f"deleted {command[1]}")
			return
		elif command[0] == "^force_update":
			if str(message.author) == "Pyronki#7387":
				try:
					api.force_update_database(command[1])
					await msgChannel.send(f"updated data for map {command[1]}")
				except:
					e_tr = traceback.format_exc()
					print(e_tr)
					return
		elif command[0] == "^update_db":
			if str(message.author) == "Pyronki#7387":
				try:
					res = api.get_top(command[1], limit=100)
					await msgChannel.send("updating..")
					for x in res:
						api.force_update_database(x["beatmap_id"])
					await msgChannel.send("done")
				except:
					e_tr = traceback.format_exc()
					print(e_tr)
					return
		elif message.content == "!stop":
			await client.logout()
		else:
			return


client = bot()
client.run(api_keys[1])
