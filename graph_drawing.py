import matplotlib.pyplot as plt
import device_tracker as dev_track
import my_utils as u

if __name__ == '__main__':
    # We'll just plot the lot of them to begin with
    device_histories = dev_track.get_all_device_history()
    f, axarr = plt.subplots(len(device_histories), sharex=True)

    for n, (device, device_history) in enumerate(device_histories):
        timeline, present = zip(*device_history)
        if device[3]:
            # Device name is present
            axarr[n].set_title('{}'.format(device[3]))
        else:
            # Using device mac
            axarr[n].set_title('{}'.format(u.int_mac_to_hex_mac(device[1])))
        axarr[n].plot(timeline, present, drawstyle='steps-mid')
        axarr[n].fill_between(timeline, 0, present, step='mid')
        axarr[n].tick_params(axis='both', which='both', bottom='off',
                             top='off', left='off', right='off')
    # Remove all Y axis lables
    plt.setp([a.get_yticklabels() for a in f.axes], visible=False)

    # Set X axis to angled
    #plt.setp([a.get_xticklabels() for a in f.axes], rotation=45)
    f.autofmt_xdate()

    plt.tight_layout(pad=0.4)
    plt.savefig('foo.png')
