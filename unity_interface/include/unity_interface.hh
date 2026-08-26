/*
PURPOSE:
    (Interface between Trick/JEOD and Unity)

LIBRARY_DEPENDENCIES:
    ((../src/unity_interface.cpp))
*/

#ifndef UNITY_INTERFACE_HH
#define UNITY_INTERFACE_HH

#include "sim_services/SimObject/include/SimObject.hh"

namespace Trick {

class UnityInterface : public SimObject
{
public:

    UnityInterface();
    virtual ~UnityInterface();

    int initialize();
    int update();

    virtual int call_function(Trick::JobData * curr_job);
    virtual double call_function_double(Trick::JobData * curr_job);

    double sim_time;

    double * position_source;
    double * velocity_source;

private:

    int socket_fd;
    void * unity_address;
};

}

#endif