JEOD_HOME ?= /home/cody/jeod

include $(JEOD_HOME)/bin/jeod/generic_S_overrides.mk

TRICK_CFLAGS += -g -I$(CURDIR)
TRICK_CXXFLAGS += -g -I$(CURDIR)