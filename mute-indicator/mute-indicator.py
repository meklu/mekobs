# Partially based on https://raw.githubusercontent.com/dmadison/OBS-Mute-Indicator/master/scripts/OBS_Mute_Indicator.py

# The next step is integrating simpleobsws somehow to gauge the volume of the
# monitored source so as to not constantly play the indicator sound when the
# monitored source is muted. The idea is to only play noise when speaking into
# a muted microphone.

# Alternatively, do as described at
# https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API#access-source-db-volume-level
# Seems a bit clunky, as it requires LD_PRELOADing libpython.so

import obspython as obs

monitored_source_name = ""
monitored_is_muted = False
indicator_source_name = ""
callback_set_for_source = None

sources_loaded = False

def sources_available() -> bool:
	global monitored_source_name, indicator_source_name
	res = True
	source = obs.obs_get_source_by_name(monitored_source_name)
	indicator = obs.obs_get_source_by_name(indicator_source_name)
	if source is not None:
		obs.obs_source_release(source)
	else:
		res = False
	if indicator is not None:
		obs.obs_source_release(indicator)
	else:
		res = False
	return res

def init_timer():
	global sources_loaded
	if not sources_available():
		return
	else:
		sources_loaded = True
		obs.timer_remove(init_timer)
		install_handler()

def install_handler():
	global callback_set_for_source, monitored_source_name
	if monitored_source_name is None or monitored_source_name == "" or monitored_source_name is callback_set_for_source:
		# don't need to do jack
		return
	uninstall_handler()
	source = obs.obs_get_source_by_name(monitored_source_name)
	handler = obs.obs_source_get_signal_handler(source)
	obs.signal_handler_connect(handler, "mute", handle_muted)
	callback_set_for_source = monitored_source_name

	obs.obs_source_release(source)

def uninstall_handler():
	global callback_set_for_source
	if callback_set_for_source is None:
		# don't need to do jack
		return
	source = obs.obs_get_source_by_name(callback_set_for_source)
	handler = obs.obs_source_get_signal_handler(source)
	obs.signal_handler_disconnect(handler, "mute", handle_muted)
	callback_set_for_source = None

	obs.obs_source_release(source)

def handle_muted(props = None, property = None):
	global monitored_source_name, indicator_source_name
	source = obs.obs_get_source_by_name(monitored_source_name)
	if not source:
		print(__file__ + ": No source set")
		return
	monitored_is_muted = obs.obs_source_muted(source)
	indicator = obs.obs_get_source_by_name(indicator_source_name)
	if not indicator:
		obs.obs_source_release(source)

		print(__file__ + ": No indicator set")
		return
	obs.obs_source_set_monitoring_type(indicator, obs.OBS_MONITORING_TYPE_MONITOR_ONLY)
	obs.obs_source_media_restart(indicator)
	obs.obs_source_set_muted(indicator, not monitored_is_muted)

	obs.obs_source_release(source)
	obs.obs_source_release(indicator)

def list_audio_sources():
	audio_sources = []
	sources = obs.obs_enum_sources()

	for source in sources:
		if obs.obs_source_get_type(source) == obs.OBS_SOURCE_TYPE_INPUT:
			# output flag bit field: https://obsproject.com/docs/reference-sources.html?highlight=sources#c.obs_source_info.output_flags
			capabilities = obs.obs_source_get_output_flags(source)

			has_audio = capabilities & obs.OBS_SOURCE_AUDIO
			# has_video = capabilities & obs.OBS_SOURCE_VIDEO
			# composite = capabilities & obs.OBS_SOURCE_COMPOSITE

			if has_audio:
				audio_sources.append(obs.obs_source_get_name(source))

	obs.source_list_release(sources)

	return audio_sources

# OBS stuffs

def script_description():
	return "<b>Mute Indicator</b>" + \
			"<hr/>" + \
			"Python script for audibly indicating mute state." + \
			"<br/><br/>" + \
			"<a>https://github.com/meklu/mekobs</a>"

def script_update(settings):
	global monitored_source_name, indicator_source_name

	monitored_source_name = obs.obs_data_get_string(settings, "monitored_source")
	indicator_source_name = obs.obs_data_get_string(settings, "indicator_source")

	if sources_loaded:
		install_handler() # try to install handler

def script_properties():
	props = obs.obs_properties_create()

	# Create list of audio sources and add them to properties list
	audio_sources = list_audio_sources()

	monitored_source_list = obs.obs_properties_add_list(
		props,
		"monitored_source",
		"Monitored Source",
		obs.OBS_COMBO_TYPE_LIST,
		obs.OBS_COMBO_FORMAT_STRING
	)

	for name in audio_sources:
		obs.obs_property_list_add_string(monitored_source_list, name, name)

	indicator_source_list = obs.obs_properties_add_list(
		props,
		"indicator_source",
		"Indicator Source",
		obs.OBS_COMBO_TYPE_LIST,
		obs.OBS_COMBO_FORMAT_STRING
	)

	for name in audio_sources:
		obs.obs_property_list_add_string(indicator_source_list, name, name)

	obs.obs_properties_add_button(props, "handle_muted", "Trigger handle_muted", handle_muted)

	return props

def script_load(settings):
	print("mute-indicator loaded")
	obs.timer_add(init_timer, 100) # try to load sources

def script_unload():
	obs.timer_remove(init_timer)
	print("mute-indicator.py unloaded")