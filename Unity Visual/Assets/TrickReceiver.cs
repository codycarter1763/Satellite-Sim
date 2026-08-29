using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class TrickReceiver : MonoBehaviour
{
    [Header("UDP")]
    [SerializeField] private int port = 5005;

    [Header("Objects")]
    [SerializeField] private Transform vehicle;
    [SerializeField] private Transform vehicle2;

    [Header("Smoothing")]
    [SerializeField] private float positionSmooth = 20f;
    [SerializeField] private float rotationSmooth = 20f;

    private const int PACKET_SIZE = 112;

    private UdpClient udp;
    private Thread receiveThread;
    private volatile bool running;

    private readonly object stateLock = new object();

    // =========================================================
    // Current received state
    // =========================================================

    private Vector3 vehiclePosition;
    private Quaternion vehicleRotation;

    private Vector3 vehicle2Position;
    private Quaternion vehicle2Rotation;

    private bool hasData;


    // =========================================================
    // Start
    // =========================================================

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


    // =========================================================
    // Receive UDP data
    // =========================================================

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


                // -------------------------------------------------
                // Validate packet size
                // -------------------------------------------------

                if (data.Length != PACKET_SIZE)
                {
                    Debug.LogWarning(
                        $"Expected {PACKET_SIZE} bytes, " +
                        $"received {data.Length}"
                    );

                    continue;
                }


                // =================================================
                // Vehicle
                //
                // Bytes 0 - 55
                // =================================================

                double vehicleX =
                    BitConverter.ToDouble(data, 0);

                double vehicleY =
                    BitConverter.ToDouble(data, 8);

                double vehicleZ =
                    BitConverter.ToDouble(data, 16);

                double vehicleW =
                    BitConverter.ToDouble(data, 24);

                double vehicleQX =
                    BitConverter.ToDouble(data, 32);

                double vehicleQY =
                    BitConverter.ToDouble(data, 40);

                double vehicleQZ =
                    BitConverter.ToDouble(data, 48);


                // =================================================
                // Vehicle 2
                //
                // Bytes 56 - 111
                // =================================================

                double vehicle2X =
                    BitConverter.ToDouble(data, 56);

                double vehicle2Y =
                    BitConverter.ToDouble(data, 64);

                double vehicle2Z =
                    BitConverter.ToDouble(data, 72);

                double vehicle2W =
                    BitConverter.ToDouble(data, 80);

                double vehicle2QX =
                    BitConverter.ToDouble(data, 88);

                double vehicle2QY =
                    BitConverter.ToDouble(data, 96);

                double vehicle2QZ =
                    BitConverter.ToDouble(data, 104);


                // =================================================
                // Store received state
                // =================================================

                lock (stateLock)
                {
                    vehiclePosition =
                        new Vector3(
                            (float)vehicleX,
                            (float)vehicleY,
                            (float)vehicleZ
                        );

                    vehicleRotation =
                        new Quaternion(
                            (float)vehicleQX,
                            (float)vehicleQY,
                            (float)vehicleQZ,
                            (float)vehicleW
                        );


                    vehicle2Position =
                        new Vector3(
                            (float)vehicle2X,
                            (float)vehicle2Y,
                            (float)vehicle2Z
                        );

                    vehicle2Rotation =
                        new Quaternion(
                            (float)vehicle2QX,
                            (float)vehicle2QY,
                            (float)vehicle2QZ,
                            (float)vehicle2W
                        );

                    hasData = true;
                }
            }
            catch (SocketException)
            {
                if (running)
                {
                    Debug.LogError(
                        "UDP socket error."
                    );
                }
            }
            catch (Exception e)
            {
                if (running)
                {
                    Debug.LogError(
                        $"UDP receive error: {e.Message}"
                    );
                }
            }
        }
    }


    // =========================================================
    // Unity frame update
    // =========================================================

    void Update()
    {
        Vector3 pos1;
        Quaternion rot1;

        Vector3 pos2;
        Quaternion rot2;


        // ---------------------------------------------------------
        // Copy latest received state
        // ---------------------------------------------------------

        lock (stateLock)
        {
            if (!hasData)
            {
                return;
            }

            pos1 = vehiclePosition;
            rot1 = vehicleRotation;

            pos2 = vehicle2Position;
            rot2 = vehicle2Rotation;
        }


        // ---------------------------------------------------------
        // Calculate frame-rate independent smoothing
        // ---------------------------------------------------------

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


        // =========================================================
        // Vehicle
        // =========================================================

        if (vehicle != null)
        {
            vehicle.position =
                Vector3.Lerp(
                    vehicle.position,
                    pos1,
                    positionT
                );

            vehicle.rotation =
                Quaternion.Slerp(
                    vehicle.rotation,
                    rot1,
                    rotationT
                );
        }


        // =========================================================
        // Vehicle 2
        // =========================================================

        if (vehicle2 != null)
        {
            vehicle2.position =
                Vector3.Lerp(
                    vehicle2.position,
                    pos2,
                    positionT
                );

            vehicle2.rotation =
                Quaternion.Slerp(
                    vehicle2.rotation,
                    rot2,
                    rotationT
                );
        }
    }


    // =========================================================
    // Shutdown
    // =========================================================

    void OnApplicationQuit()
    {
        running = false;

        try
        {
            udp?.Close();
        }
        catch
        {
            // Ignore shutdown errors.
        }

        try
        {
            if (receiveThread != null &&
                receiveThread.IsAlive)
            {
                receiveThread.Join(500);
            }
        }
        catch
        {
            // Ignore shutdown errors.
        }
    }
}