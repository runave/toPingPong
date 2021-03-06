#!/usr/bin/python

import codecs
import json
import os
import time

ScriptName = "toPingPong"
Website = "https://github.com/runave/toPingPong"
Creator = "runave"
Version = "0.3"
Description = "Ping-pong for life and death"

settingsFile = os.path.join(os.path.dirname(__file__), "settings.json")

class Settings:
  def __init__(self, settingsFile=None):
    self.onlyWhenLive = True
    self.protectedCooldown = 1800
    self.minTimeout = 600
    self.maxTimeout = 900
    self.incrChance = 20
    self.incrTimeout = 60
    self.pingCommand = "!ping"
    self.pingCost = 50
    self.pongCommand = "!pong"
    self.pongCost = 100
    self.pongTime = 60
    self.pingModCommand = "!ping"
    self.pingModCost = 500
    self.noPointsResponse = "$user, you need more points ($cost) to do that!"
    self.noTargetResponse = "$user, who do you want to serve the TO ball to?"
    self.pingResponse = "$user served the TO ball to $target! Type $command in $seconds seconds to return it back!"
    self.pongResponse = "$user returned the TO ball to $target! Type $command in $seconds seconds to return it back!"
    self.pongIncrResponse = "$user returned the TO ball to $target with extreme spin, causing a slight increase in TO! Type $command in $seconds seconds to return it back!"
    self.winResponse = "$user won the TO ping-pong game against $target!"
    self.protectedResponse = "$user tried to serve the TO ball to $target but it did not land on the table!"
    self.timeoutCommand = "/timeout $target $seconds"
    if settingsFile and os.path.isfile(settingsFile):
      with codecs.open(settingsFile, encoding='utf-8-sig', mode='r') as f:
        self.__dict__.update(json.load(f, encoding='utf-8-sig'))

  def Reload(self, data):
    self.__dict__ = json.loads(data, encoding='utf-8-sig')

  def Save(self, settingsFile):
    try:
      with codecs.open(settingsFile, encoding="utf-8-sig", mode="w+") as f:
        json.dump(self.__dict__, f, encoding="utf-8", ensure_ascii=False)
      with codecs.open(settingsFile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
        f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8', ensure_ascii=False)))
    except ValueError:
      Parent.Log(ScriptName, "Failed to save settings to file.")

class State:
  def __init__(self, user, timeout):
    self.user = user
    self.startTime = time.time()
    self.timeout = timeout

def SendResponse(msg, msgParams):
  if msg:
    # replace params with actual values, e.g. $user -> pistike
    for key in msgParams:
      msg = msg.replace(key, msgParams[key])
    Parent.SendStreamMessage(msg)
  return

def AlreadyPlaying(user):
  if user in state:
    return True
  for key in state:
    if state[key].user == user:
      return True
  return False

def Init():
  global settings
  settings = Settings(settingsFile)
  global state
  state = {}
  return

def ReloadSettings(data):
  global settings
  settings.Reload(data)

def SaveSettings():
  global settings
  settings.Save(data)

def PayCost(data, cost):
  global settings
  if Parent.GetPoints(data.User) < int(cost):
    SendResponse(settings.noPointsResponse, {"$user": data.UserName, "$cost": str(cost)})
    return False
  Parent.RemovePoints(data.User, data.UserName, int(cost))
  return True

def Tick():
  global settings
  global state
  now = time.time()
  for target in list(state):
    data = state[target]
    if now - data.startTime > settings.pongTime:
      del state[target]
      SendResponse(settings.winResponse, {"$user": Parent.GetDisplayName(data.user), "$target": Parent.GetDisplayName(target)})
      SendResponse(settings.timeoutCommand, {"$target": target, "$seconds": str(data.timeout)})
      if settings.protectedCooldown > 0:
        Parent.AddUserCooldown(ScriptName, "protected", target, settings.protectedCooldown)
  return

def Execute(data):
  global settings
  global state

  if data.IsChatMessage():
    command = data.GetParam(0).lower()

    if command == settings.pongCommand.lower():
      if not settings.onlyWhenLive or Parent.IsLive():
        if data.User in state:
          if not PayCost(data, settings.pongCost):
            return
          target = state[data.User].user
          timeout = state[data.User].timeout
          incrCond = settings.incrChance > 0 and timeout < settings.maxTimeout and settings.incrChance >= Parent.GetRandom(1, 100)
          if incrCond:
            # lets slightly increase the timeout
            timeout = timeout + settings.incrTimeout
            if timeout > settings.maxTimeout:
              timeout = settings.maxTimeout
          del state[data.User]
          state[target] = State(data.User, timeout)
          SendResponse(settings.pongIncrResponse if incrCond else settings.pongResponse, {"$user": data.UserName, "$target": Parent.GetDisplayName(target), "$command": settings.pongCommand, "$seconds": str(settings.pongTime)})
          return

    if command == settings.pingCommand.lower() or command == settings.pingModCommand.lower():
      if not settings.onlyWhenLive or Parent.IsLive():
        target = data.GetParam(1).lower()
        if target and target[0] == '@':
          target = target[1:] # remove @ prefix from target name
        if not target:
          SendResponse(settings.noTargetResponse, {"$user": data.UserName})
          return
        if target == data.User:
          return
        if target not in Parent.GetViewerList() and target not in Parent.GetActiveUsers():
          return
        cost = settings.pingCost
        if Parent.HasPermission(target, "Moderator", ""):
          if not command == settings.pingModCommand.lower():
            return # wrong command
          cost = settings.pingModCost
        if AlreadyPlaying(data.User) or AlreadyPlaying(target) or Parent.IsOnUserCooldown(ScriptName, "protected", target):
          SendResponse(settings.protectedResponse, {"$user": data.UserName, "$target": Parent.GetDisplayName(target)})
          return
        if not PayCost(data, cost):
          return
        state[target] = State(data.User, settings.minTimeout)
        SendResponse(settings.pingResponse, {"$user": data.UserName, "$target": Parent.GetDisplayName(target), "$command": settings.pongCommand, "$seconds": str(settings.pongTime)})
        return

  return
