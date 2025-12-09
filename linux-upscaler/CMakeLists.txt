cmake_minimum_required(VERSION 3.10)
project(linux_upscaler)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(X11 REQUIRED)
find_package(OpenGL REQUIRED)

include_directories(
    ${X11_INCLUDE_DIR}
    ${OPENGL_INCLUDE_DIRS}
)

set(SOURCES
    src/main.cpp
    src/capture/capture_wrapper.cpp
    src/renderer/renderer_gl.cpp
    # Add other source files as needed
)

add_executable(\${PROJECT_NAME} \${SOURCES})

target_link_libraries(\${PROJECT_NAME}
    \${X11_LIBRARIES}
    \${OPENGL_LIBRARIES}
    GL
    Xext
)
