# CP found at /home/cody/trick/bin

# Disable built-in implicit rules to increase build speed.

.SUFFIXES:

.PHONY: all

ifndef TRICK_HOME
    export TRICK_HOME := /home/cody/trick
endif

-include S_pre.mk

ifneq ($(wildcard ${TRICK_HOME}/share/trick/makefiles/Makefile.common),)
include ${TRICK_HOME}/share/trick/makefiles/Makefile.common

ifndef TRICK_VERBOSE_BUILD
    PRINT_CP            = $(info $(call COLOR,Running)    configuration_processor)
    PRINT_ICG           = $(info $(call COLOR,Running)    ICG)
    PRINT_MAKEFILE_SRC  = $(info $(call COLOR,Writing)    Makefile_src)
    PRINT_MAKEFILE_SWIG = $(info $(call COLOR,Writing)    Makefile_swig)
endif

all:
	$(info [32mTrick Build Process Complete[00m)

test: TRICK_SYSTEM_CFLAGS += -DTRICK_UNIT_TEST
test: TRICK_SYSTEM_CXXFLAGS += -DTRICK_UNIT_TEST
test: all

debug: TRICK_CPFLAGS += --debug
debug: all

build:
	@mkdir -p $@

$(TRICK_STATIC_LIB):
	$(info Cannot find $@. Please build Trick for this platform.)
	@exit -1

# CP creates S_source.hh required for ICG and SWIG processing
S_source.hh: S_define | build
	$(PRINT_CP)
	$(call ECHO_AND_LOG,${TRICK_HOME}/$(LIBEXEC)/trick/configuration_processor $(TRICK_CPFLAGS))

build/Makefile_S_define: S_source.hh
	$(PRINT_S_DEF_DEPS)
	$(call ECHO_AND_LOG,$(TRICK_CXX) $(TRICK_SFLAGS) $(TRICK_SYSTEM_SFLAGS) -MM -MT S_source.hh -MF build/Makefile_S_define -x c++ S_define)

# Automatic and manual ICG rules
ICG:
	$(PRINT_ICG)
	$(call ECHO_AND_LOG,${TRICK_HOME}/bin/trick-ICG -m ${TRICK_ICGFLAGS} ${TRICK_CXXFLAGS} ${TRICK_SYSTEM_CXXFLAGS} S_source.hh)


force_ICG:
	$(PRINT_ICG)
	$(call ECHO_AND_LOG,${TRICK_HOME}/bin/trick-ICG -force -m ${TRICK_ICGFLAGS} ${TRICK_CXXFLAGS} ${TRICK_SYSTEM_CXXFLAGS} S_source.hh)

# Create makefile for IO code
build/Makefile_io_src: S_source.hh | build
	$(PRINT_ICG)
	$(call ECHO_AND_LOG,${TRICK_HOME}/bin/trick-ICG -m ${TRICK_ICGFLAGS} ${TRICK_CXXFLAGS} ${TRICK_SYSTEM_CXXFLAGS} $<)

# Create makefile for source code
build/Makefile_src: build/Makefile_src_deps build/Makefile_io_src S_source.hh
	$(PRINT_MAKEFILE_SRC)
	$(call ECHO_AND_LOG,${TRICK_HOME}/$(LIBEXEC)/trick/make_makefile_src $? 2>&1)

build/Makefile_src_deps: ;

# Create makefile for SWIG code
build/Makefile_swig: S_source.hh build/Makefile_swig_deps
	$(PRINT_MAKEFILE_SWIG)
	$(call ECHO_AND_LOG,${TRICK_HOME}/$(LIBEXEC)/trick/make_makefile_swig)

build/Makefile_swig_deps: ;

# Forcibly (re)create all SWIG input (.i) files. This rule is never run by the normal
# build process.
.PHONY: convert_swig
convert_swig: build/S_library_swig
	$(call ECHO_AND_LOG,${TRICK_HOME}/$(LIBEXEC)/trick/convert_swig ${TRICK_CONVERT_SWIG_FLAGS})

# Force S_define_exp to be remade each time this rule runs
.PHONY: S_define_exp
S_define_exp:
	$(TRICK_CC) -E -C -xc++ ${TRICK_SFLAGS} $(TRICK_SYSTEM_SFLAGS) S_define > $@

# prints the value of a makefile variable, example invocation "make print-TRICK_CXXFLAGS"
# This rule is used by trick-config
print-%:
	@echo '$*=$($*)'

help:
	@echo -e "\
Simulation make options:\n\
    make [debug] [TRICK_VERBOSE_BUILD=1] [VERBOSE=1] - Makes everything: S_main and S_sie.resource\n\
    make sie                     - Builds the S_sie.resource file.\n\
    make clean                   - Removes all object files in simulation directory\n\
    make spotless                - Performs a clean\n\
    make apocalypse              - Performs a clean\n\
    make print-<variable>        - Prints a makefile or environment variable"

CLEAN_TARGETS = tidy clean spotless distclean apocalypse
ifdef AM_I_TRICKIFYING
include build/Makefile_S_define
include build/Makefile_src
else ifeq ($(findstring ${MAKECMDGOALS},$(CLEAN_TARGETS)),)
include build/Makefile_S_define
include build/Makefile_src
include build/Makefile_src_deps
include build/Makefile_io_src
include build/Makefile_swig
include build/Makefile_swig_deps
-include build/Makefile_ICG
endif
-include build/Makefile_overrides
-include S_overrides.mk
-include trickify.mk
-include S_post.mk

ifndef MAKE_RESTARTS
REMOVE_MAKE_OUT := $(shell rm -f $(MAKE_OUT))
ifeq ($(MAKECMDGOALS),)
    $(info $(call COLOR,Building with the following compilation flags:))
    $(info TRICK_CFLAGS   = [36m$(TRICK_CFLAGS)[0m)
    $(info TRICK_CXXFLAGS = [36m$(TRICK_CXXFLAGS)[0m)
endif
endif

else
all:
	$(error error with TRICK_HOME, cannot find ${TRICK_HOME}/share/trick/makefiles/Makefile.common)
endif

tidy:
	-rm -f S_source.hh S_sie.resource S_sie.json
	-rm -f S_main* T_main*
	-rm -f build/Makefile_*

clean: tidy
	-rm -f DP_Product/DP_rt_frame DP_Product/DP_rt_itimer
	-rm -f DP_Product/DP_rt_jobs DP_Product/DP_rt_timeline DP_Product/DP_mem_stats
	-rm -rf build .trick trick.zip
	-rm -f makefile

spotless: clean

distclean: clean

apocalypse: clean clean_trickify
	@echo "[31mI love the smell of napalm in the morning <3[0m"

clean_trickify: ;
nuke_trickify: ;
