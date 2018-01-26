# ======================================================================
#  artdaq-daqinterface main build file
#
#  cd .../path/to/build/directory
#  source .../path/to/artdaq-utilities/ups/setup_for_development
#  cmake [-DCMAKE_INSTALL_PREFIX=/install/path]
#        -Dqualifier:STRING=$CETPKG_QUAL
#        -DCMAKE_BUILD_TYPE=$CETPKG_TYPE
#        $CETPKG_SOURCE
#  make
#  make test
#  make install
#  make package
# ======================================================================

# use cmake 2.8 or later
cmake_minimum_required (VERSION 2.8)

project(artdaq-daqinterface)
# cetbuildtools contains our cmake modules
SET ( CETBUILDTOOLS_VERSION $ENV{CETBUILDTOOLS_VERSION} )
IF (NOT CETBUILDTOOLS_VERSION)
    MESSAGE (FATAL_ERROR "ERROR: setup cetbuildtools to get the cmake modules")
ENDIF()

set(CMAKE_MODULE_PATH $ENV{CETBUILDTOOLS_DIR}/Modules
		      ${CMAKE_MODULE_PATH})

include(CetCMakeEnv)
cet_cmake_env(noarch)

cet_set_compiler_flags(DIAGS VIGILANT
  WERROR
  NO_UNDEFINED
  EXTRA_FLAGS -pedantic
)

string(TOUPPER ${CMAKE_BUILD_TYPE} BTYPE_UC )
#if( ${BTYPE_UC} MATCHES "DEBUG" )
#  cet_add_compiler_flags(-fsanitize=address)
#endif()

cet_report_compiler_flags()

# these are minimum required versions, not the actual product versions
find_ups_product (cetbuildtools v4_09_02)
find_ups_product( cetpkgsupport v1_08_03 )

# ups - table and config files
add_subdirectory(ups)

# Copy from source to install
FILE(COPY bin DESTINATION .)
INSTALL(DIRECTORY bin DESTINATION ${product}/${version})
FILE(COPY docs DESTINATION .)
INSTALL(DIRECTORY docs DESTINATION ${product}/${version})
FILE(COPY rc DESTINATION .)
INSTALL(DIRECTORY rc DESTINATION ${product}/${version})
FILE(COPY simple_test_config DESTINATION .)
INSTALL(DIRECTORY simple_test_config DESTINATION ${product}/${version})
FILE(COPY utils DESTINATION .)
INSTALL(DIRECTORY utils DESTINATION ${product}/${version})
FILE(COPY source_me DESTINATION .)
INSTALL(FILES source_me DESTINATION ${product}/${version})
#FILE(COPY .components.txt DESTINATION .)
#INSTALL(FILES .components.txt DESTINATION ${product}/${version})
#FILE(COPY .settings DESTINATION .)
#INSTALL(FILES .settings DESTINATION ${product}/${version})

# packaging utility
include(UseCPack)
