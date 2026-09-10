using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class TrickReceiver : MonoBehaviour
{
    [SerializeField] int port = 5005;
    [SerializeField] Transform vehicle;
    [SerializeField] EarthRotation earthRotation;
    [SerializeField] GroundTrack groundTrack;

    [SerializeField] float metersToUnity = 0.000001f;
    [SerializeField] bool swapYZ;
    [SerializeField] bool invertX;
    [SerializeField] bool invertY;
    [SerializeField] bool invertZ;

    [SerializeField] float positionSmooth = 20f;
    [SerializeField] float rotationSmooth = 20f;

    const int PACKET_SIZE = 88;

    UdpClient udp;
    Thread receiveThread;
    bool running;

    readonly object stateLock = new object();

    Vector3 position;
    Quaternion rotation;
    double simTime;
    double latitude;
    double longitude;
    double altitude;
    bool hasData;

    void Start()
    {
        try
        {
            udp = new UdpClient(port);
            running = true;

            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log($"Listening on UDP port {port}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Could not start receiver: {e.Message}");
        }
    }

    void ReceiveData()
    {
        IPEndPoint endpoint = new IPEndPoint(IPAddress.Any, port);

        while (running)
        {
            try
            {
                byte[] data = udp.Receive(ref endpoint);

                if (data.Length != PACKET_SIZE)
                    continue;

                simTime = BitConverter.ToDouble(data, 0);

                double x = BitConverter.ToDouble(data, 8);
                double y = BitConverter.ToDouble(data, 16);
                double z = BitConverter.ToDouble(data, 24);

                double qw = BitConverter.ToDouble(data, 32);
                double qx = BitConverter.ToDouble(data, 40);
                double qy = BitConverter.ToDouble(data, 48);
                double qz = BitConverter.ToDouble(data, 56);

                double lat = BitConverter.ToDouble(data, 64);
                double lon = BitConverter.ToDouble(data, 72);
                double alt = BitConverter.ToDouble(data, 80);

                float px = (float)(x * metersToUnity);
                float py = (float)(y * metersToUnity);
                float pz = (float)(z * metersToUnity);

                if (swapYZ)
                {
                    float temp = py;
                    py = pz;
                    pz = temp;
                }

                if (invertX) px = -px;
                if (invertY) py = -py;
                if (invertZ) pz = -pz;

                Quaternion rot = new Quaternion(
                    (float)qx,
                    (float)qy,
                    (float)qz,
                    (float)qw
                );

                rot.Normalize();

                lock (stateLock)
                {
                    position = new Vector3(px, py, pz);
                    rotation = rot;
                    latitude = lat;
                    longitude = lon;
                    altitude = alt;
                    hasData = true;
                }
            }
            catch (Exception e)
            {
                if (running)
                    Debug.LogError($"UDP error: {e.Message}");
            }
        }
    }

    void Update()
    {
        lock (stateLock)
        {
            if (!hasData)
                return;

            if (earthRotation != null)
                earthRotation.SetSimulationTime(simTime);

            if (groundTrack != null)
                groundTrack.SetPosition(
                    (float)latitude,
                    (float)longitude,
                    (float)altitude
                );

            if (vehicle == null)
                return;

            float positionT = 1f - Mathf.Exp(-positionSmooth * Time.deltaTime);
            float rotationT = 1f - Mathf.Exp(-rotationSmooth * Time.deltaTime);

            vehicle.position = Vector3.Lerp(
                vehicle.position,
                position,
                positionT
            );

            vehicle.rotation = Quaternion.Slerp(
                vehicle.rotation,
                rotation,
                rotationT
            );
        }
    }

    void OnApplicationQuit()
    {
        running = false;

        if (udp != null)
            udp.Close();

        if (receiveThread != null && receiveThread.IsAlive)
            receiveThread.Join(500);
    }
}
