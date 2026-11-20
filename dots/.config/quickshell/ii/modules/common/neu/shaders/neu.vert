#version 440
// The vertex stage for neumorph.frag: Qt's default one, compiled for the same GLSL versions as the fragment shader
// (Qt's own default vertex shader is not, and the two then fail to link on OpenGL).
layout(location = 0) in vec4 qt_Vertex;
layout(location = 1) in vec2 qt_MultiTexCoord0;
layout(location = 0) out vec2 qt_TexCoord0;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
};
void main() {
    qt_TexCoord0 = qt_MultiTexCoord0;
    gl_Position = qt_Matrix * qt_Vertex;
}
