#include "../include/unity_interface.hh"

#include <cstdio>
#include <cstring>

#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>

namespace Trick {

UnityInterface::UnityInterface()
    : sim_time(0.0),
      position_source(nullptr),
      velocity_source(nullptr),
      socket_fd(-1),
      unity_address(nullptr)
{
}

UnityInterface::~UnityInterface()
{
    if (socket_fd >= 0) {
        close(socket_fd);
    }

    delete static_cast<sockaddr_in *>(unity_address);
}

int UnityInterface::initialize()
{
    socket_fd = socket(AF_INET, SOCK_DGRAM, 0);

    if (socket_fd < 0) {
        perror("UnityInterface: socket");
        return -1;
    }

    auto * addr = new sockaddr_in();

    std::memset(addr, 0, sizeof(sockaddr_in));

    addr->sin_family = AF_INET;
    addr->sin_port = htons(5005);

    if (inet_pton(AF_INET, "127.0.0.1", &addr->sin_addr) != 1) {
        perror("UnityInterface: inet_pton");
        delete addr;
        return -1;
    }

    unity_address = addr;

    printf("UnityInterface: UDP initialized\n");

    return 0;
}

int UnityInterface::update()
{
    if (socket_fd < 0 ||
        unity_address == nullptr ||
        position_source == nullptr ||
        velocity_source == nullptr) {
        return -1;
    }

    struct StatePacket
    {
        double time;
        double position[3];
        double velocity[3];
    };

    StatePacket packet;

    packet.time = sim_time;

    for (int i = 0; i < 3; ++i) {
        packet.position[i] = position_source[i];
        packet.velocity[i] = velocity_source[i];
    }

    auto * addr = static_cast<sockaddr_in *>(unity_address);

    ssize_t bytes_sent = sendto(
        socket_fd,
        &packet,
        sizeof(packet),
        0,
        reinterpret_cast<sockaddr *>(addr),
        sizeof(sockaddr_in)
    );

    if (bytes_sent < 0) {
        perror("UnityInterface: sendto");
        return -1;
    }

    return 0;
}

int UnityInterface::call_function(Trick::JobData * curr_job)
{
    (void)curr_job;
    return 0;
}

double UnityInterface::call_function_double(Trick::JobData * curr_job)
{
    (void)curr_job;
    return 0.0;
}

}