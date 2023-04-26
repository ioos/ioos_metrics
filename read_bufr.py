fname = 'bufr_messages/profile_1022794800.bufr'

import pdbufr
#fname = 'https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/ct169-594-21/profile_1023825600.bufr'
df_bufr = pdbufr.read_bufr(fname, flat=True, columns="data")

# df_bufr = pdbufr.read_bufr(fname,
#                            columns=("latitude","longitude","data_datetime","depthBelowWaterSurface"),
#                            )