#version 130
in vec4 p3d_Vertex;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelMatrix;

out vec3 world_pos;
out float view_z;

void main()
    {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    world_pos= vec4(p3d_ModelMatrix * p3d_Vertex).xyz;
    view_z=-vec4(p3d_ModelViewMatrix * p3d_Vertex).z;
    }
