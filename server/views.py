#Base
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import datetime
import time
import logging
import urllib2, urllib
import hashlib
import json, uuid
import os, base64

#Authentication and Permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

#Models
from server.models import Venue, UserProfile, Gang, Message
from django.contrib.auth.models import User

#Serializers
from server.serializers import VenueSerializer, UserProfileSerializer, GangSerializer, UserSerializer, MessageSerializer

from django.http import HttpResponse

class VenueViewSet(viewsets.ModelViewSet):
	authentication_classes = (SessionAuthentication, BasicAuthentication)
#	permission_classes = (IsAuthenticated,)
	queryset = Venue.objects.all()
	serializer_class = VenueSerializer

def getHeatMapData(request, event, timestamp):
	#Yesterday
	if timestamp == 'y':
		start = datetime.date.today() - datetime.timedelta(1)
		start = start.strftime("%s")
		end = time.time()
	elif timestamp == 'a':
		start = 1394100066
		end = 1399459452
	end = round(end, 0)
	print start, end
	
	mac = ''.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])
        mac = ''.join([x.upper() for x in mac])

        m = hashlib.sha1()
        m.update(mac)
        user_id = m.hexdigest().upper()

	game_key = 'f58c639185081f602fee6f6b725349b7'
	api_key = "3e2ca2703b96e4a27c3ccf450da9a9ba29946237"
	secret_key = '10d560a88e6b0050f8a42a60e806f5fc909f9ad3'
	
	url = 'http://data-api.gameanalytics.com/heatmap/?'	
	
	encoding = urllib.urlencode([('game_key',game_key), ('event_ids',str(event)), ('area','Oulu3D'), ('start_ts',start), ('end_ts',end)])
	
	digest = hashlib.md5()
        digest.update(encoding)
	digest.update(api_key)
	
        json_authorization = {'Authorization' : digest.hexdigest()}

	request = urllib2.Request(url+encoding, None, json_authorization)
        print encoding 
	response = urllib2.urlopen(request)
        print response.read()
        jsonres = json.dumps(response.read())	
        
	print jsonres
	return HttpResponse('<html><body>Event sent!</body></html>')


def eventHappened(request, eventId, playername, playergang, playerpos):
	game_key = 'f58c639185081f602fee6f6b725349b7'
	secret_key = '10d560a88e6b0050f8a42a60e806f5fc909f9ad3'
	endpoint_url = 'http://api.gameanalytics.com/1'
	
	mac = ''.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])
	mac = ''.join([x.upper() for x in mac])
	
	m = hashlib.sha1()
	m.update(mac)
	user_id = m.hexdigest().upper()	
	
	category = 'design'
	
	message = {}
	eventId = int(eventId)
	
	#make position from string so split from ,
	playerposi = playerpos.split('%2C')

	print playerpos , " joo " , len(playerpos)
	#req fields
	if eventId == 1:
		message["event_id"] = "spray:" + str(playergang)
	elif eventId == 2:
		message["event_id"] = "policebust:" + str(playergang)
	elif eventId == 3:
		message["event_id"] = "playerbust:" + str(playergang)
	
	message["user_id"] = user_id
	message["session_id"] = str(base64.b64encode(os.urandom(16)))
	message["build"] = "1.0a"
	message["area"] = "Oulu3D"
	message['x'] = float(playerposi[0])
	message['y'] = float(playerposi[1])
	message['z'] = float(playerposi[2])
	#message['value'] = 'playergang:'+playergang
	
	#later add location somehow (maybe pass array in url?)
	print message
	json_message = json.dumps(message)
	digest = hashlib.md5()
	digest.update(json_message)
	digest.update(secret_key)
	json_authorization = {'Authorization' : digest.hexdigest()}

	url = "%s/%s/%s" % (endpoint_url, game_key, category)
	request = urllib2.Request(url, json_message, json_authorization)
		
	response = urllib2.urlopen(request)
	print response.read()
  
	return HttpResponse('<html><body>Event sent!</body></html>')

def policeBust(request, gangsterId):
	queryset = UserProfile.objects.get(pk=gangsterId)
	queryset.bustedviapolice = 1
	queryset.busted = queryset.busted + 1
	queryset.points = queryset.points - 30
	queryset.save()
	return HttpResponse('<html><body>Jes %s</body></html>' % queryset)

class MessageViewSet(viewsets.ModelViewSet):
	authentication_classes = (SessionAuthentication, BasicAuthentication)
#	permission_classes = (IsAuthenticated,)

	queryset = Message.objects.all()
	serializer_class = MessageSerializer

	def get_queryset(self):
		"""
		Act according to the query paramethers in the get request

		"""
		queryset = Message.objects.all()

		gang = self.request.QUERY_PARAMS.get('gang', None)
		if gang is not None:
			queryset = queryset.filter(gangster__gang=gang)

		#This must be the last slice taken on the queryset.
		limit = self.request.QUERY_PARAMS.get('limit', None)
		if limit is not None:
			queryset = queryset[:limit]
		return queryset

class UserProfileViewSet(viewsets.ModelViewSet):
	authentication_classes = (SessionAuthentication, BasicAuthentication)
#	permission_classes = (IsAuthenticated,)
	serializer_class = UserProfileSerializer
	queryset = UserProfile.objects.all()

	
	
	def get_queryset(self):
		"""
		Optionally restricts the returned profiles.
		"""
		queryset = UserProfile.objects.all()
		active = self.request.QUERY_PARAMS.get('active', None)
		if active is not None:
			queryset = queryset.filter(last_action__gte=timezone.now() - datetime.timedelta(seconds=30))
		
		return queryset		

	
class GangViewSet(viewsets.ModelViewSet):
	authentication_classes = (SessionAuthentication, BasicAuthentication)
#	permission_classes = (IsAuthenticated,)
	queryset = Gang.objects.all()
	serializer_class = GangSerializer

class UserViewSet(viewsets.ModelViewSet):
	authentication_classes = (SessionAuthentication, BasicAuthentication)
#	permission_classes = (IsAuthenticated,)
	queryset = User.objects.all()
	serializer_class = UserSerializer
	
	
class UserAuthView(APIView):

	#Login. Returns the current user.
	def get(self, request, *args, **kwargs):
		# Only UserProfileSerializer is required to serialize data since
		# email is populated by the 'source' param on EmailField.
		if (request.user.is_authenticated()):
			serializer = UserProfileSerializer(
					instance=request.user.profile)
			return Response(serializer.data, status=status.HTTP_200_OK)

		return Response(status=status.HTTP_401_UNAUTHORIZED)


	#Register new user.
	def post(self, request, format=None):
		user_serializer = UserSerializer(data=request.DATA)
		errors = dict()
		if user_serializer.is_valid():
			user =user_serializer.save()
			data = request.DATA.copy()
			data['user'] = User.objects.latest('id').id
			user_profile_serializer = UserProfileSerializer(data=data)

			if user_profile_serializer.is_valid():
				user_profile_serializer.save()
				return Response(user_profile_serializer.data, status=status.HTTP_201_CREATED)

			errors.update(user_profile_serializer.errors)
			return Response(errors, status=status.HTTP_400_BAD_REQUEST)


		errors.update(user_serializer.errors)
		return Response(errors, status=status.HTTP_400_BAD_REQUEST)
