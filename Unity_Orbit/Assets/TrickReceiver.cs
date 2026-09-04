using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class TrickReceiver : MonoBehaviour
{
    [Header("UDP")]
    [SerializeField] private int port = 5005;

    [Header("Object")]
    [SerializeField] private Transform vehicle;

    [Header("Ground Track")]
    [SerializeField] private GroundTrack groundTrack;

    [Header("Simulation Scale")]
    [SerializeField] private float metersToUnity = 0.000001f;

    [Header("Coordinate System")]
    [SerializeField] private bool swapYZ = false;
    [SerializeField] private bool invertX = false;
    [SerializeField] private bool invertY = false;
    [SerializeField] private bool invertZ = false;

    [Header("Smoothing")]
    [SerializeField] private float positionSmooth = 20f;
    [SerializeField] private float rotationSmooth = 20f;

    // 11 doubles = 88 bytes
    private const int PACKET_SIZE = 88;

    private UdpClient udp;
    private Thread receiveThread;
    private volatile bool running;

    private readonly object stateLock = new object();

    private Vector3 vehiclePosition;
    private Quaternion vehicleRotation;

    private double latitude;
    private double longitude;
    private double altitude;

    private bool hasData;

    void Start()
    {
        try
        {
            udp = new UdpClient(port);

            running = true;

            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log(
                $"Listening for Trick data on UDP port {port}"
            );
        }
        catch (Exception e)
        {
            Debug.LogError(
                $"Failed to start UDP receiver: {e.Message}"
            );
        }
    }

    void ReceiveData()
    {
        IPEndPoint endpoint =
            new IPEndPoint(
                IPAddress.Any,
                port
            );

        while (running)
        {
            try
            {
                byte[] data =
                    udp.Receive(ref endpoint);

                if (data.Length != PACKET_SIZE)
                {
                    Debug.LogWarning(
                        $"Expected {PACKET_SIZE} bytes, " +
                        $"received {data.Length}"
                    );

                    continue;
                }

                // =================================================
                // Packet
                // =================================================

                double simTime =
                    BitConverter.ToDouble(data, 0);

                double vehicleX =
                    BitConverter.ToDouble(data, 8);

                double vehicleY =
                    BitConverter.ToDouble(data, 16);

                double vehicleZ =
                    BitConverter.ToDouble(data, 24);

                double vehicleW =
                    BitConverter.ToDouble(data, 32);

                double vehicleQX =
                    BitConverter.ToDouble(data, 40);

                double vehicleQY =
                    BitConverter.ToDouble(data, 48);

                double vehicleQZ =
                    BitConverter.ToDouble(data, 56);

                double lat =
                    BitConverter.ToDouble(data, 64);

                double lon =
                    BitConverter.ToDouble(data, 72);

                double alt =
                    BitConverter.ToDouble(data, 80);

                // =================================================
                // Position
                // =================================================

                float x =
                    (float)(vehicleX * metersToUnity);

                float y =
                    (float)(vehicleY * metersToUnity);

                float z =
                    (float)(vehicleZ * metersToUnity);

                if (swapYZ)
                {
                    float temp = y;
                    y = z;
                    z = temp;
                }

                if (invertX)
                    x = -x;

                if (invertY)
                    y = -y;

                if (invertZ)
                    z = -z;

                Vector3 newPosition =
                    new Vector3(
                        x,
                        y,
                        z
                    );

                // =================================================
                // Quaternion
                // =================================================

                Quaternion newRotation =
                    new Quaternion(
                        (float)vehicleQX,
                        (float)vehicleQY,
                        (float)vehicleQZ,
                        (float)vehicleW
                    );

                newRotation.Normalize();

                // =================================================
                // Store
                // =================================================

                lock (stateLock)
                {
                    vehiclePosition = newPosition;
                    vehicleRotation = newRotation;

                    latitude = lat;
                    longitude = lon;
                    altitude = alt;

                    hasData = true;
                }
            }
            catch (SocketException)
            {
                if (running)
                    Debug.LogError("UDP socket error.");
            }
            catch (Exception e)
            {
                if (running)
                    Debug.LogError(
                        $"UDP receive error: {e.Message}"
                    );
            }
        }
    }

    void Update()
    {
        Vector3 pos;
        Quaternion rot;

        double lat;
        double lon;
        double alt;

        lock (stateLock)
        {
            if (!hasData)
                return;

            pos = vehiclePosition;
            rot = vehicleRotation;

            lat = latitude;
            lon = longitude;
            alt = altitude;
        }

        // =========================================================
        // Update ground track
        // =========================================================

        if (groundTrack != null)
        {
            groundTrack.SetPosition(
                (float)lat,
                (float)lon,
                (float)alt
            );
        }

        // =========================================================
        // Smooth spacecraft
        // =========================================================

        float positionT =
            1f - Mathf.Exp(
                -positionSmooth *
                Time.deltaTime
            );

        float rotationT =
            1f - Mathf.Exp(
                -rotationSmooth *
                Time.deltaTime
            );

        if (vehicle != null)
        {
            vehicle.position =
                Vector3.Lerp(
                    vehicle.position,
                    pos,
                    positionT
                );

            vehicle.rotation =
                Quaternion.Slerp(
                    vehicle.rotation,
                    rot,
                    rotationT
                );
        }
    }

    void OnApplicationQuit()
    {
        running = false;

        try
        {
            udp?.Close();
        }
        catch
        {
        }

        try
        {
            if (
                receiveThread != null &&
                receiveThread.IsAlive
            )
            {
                receiveThread.Join(500);
            }
        }
        catch
        {
        }
    }
}