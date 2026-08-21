# Scribe Nib Firmware — CMakeLists.txt
# ESP-IDF build configuration for ESP32-S3

cmake_minimum_required(VERSION 3.16)

set(SCRIBE_NIB_VERSION "1.0.0")

# ESP-IDF project
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(scribe_nib)

# Custom partition table to include langmodel partition
# (2MB for n-gram language model data)
set(PARTITION_CSV "${CMAKE_SOURCE_DIR}/partitions.csv")
idf_build_set_property(PARTITION_CSV_PATH "${PARTITION_CSV}")

# TFLite Micro component (if building with model support)
# set(EXTRA_COMPONENT_DIRS "components")