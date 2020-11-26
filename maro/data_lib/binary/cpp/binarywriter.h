// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

#ifndef _MARO_DATALIB_BINARY_WRITER_
#define _MARO_DATALIB_BINARY_WRITER_

#include <time.h>
#include <iostream>
#include <fstream>
#include <string>
#include <map>

#include "csv2/csv2.hpp"
#include "metaparser.h"

using namespace std;

using CSV = csv2::Reader<csv2::delimiter<','>,
                         csv2::quote_character<'\"'>,
                         csv2::first_row_is_header<true>,
                         csv2::trim_policy::trim_characters<' ', '\"'>>;

namespace maro
{
    namespace datalib
    {
        const string DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S";

        class BinaryWriter
        {
        public:
            BinaryWriter();
            BinaryWriter(const BinaryWriter &writer) = delete;

            ~BinaryWriter();

            void open(string output_folder, string file_name, string file_type = "NA", int32_t file_version = 0);

            // load meta file, and generate meta info
            void load_meta(string meta_file);

            // load and convert
            void add_csv(string csv_file);

            void set_start_timestamp(ULONGLONG start_timestamp);

        private:
            char local_utc_offset = MINCHAR;
            bool _is_start_timestamp_set = false;

            // seams FILE is faster than ofstream
            ofstream _file;
            BinHeader _header;

            Meta _meta;

            char _buffer[BUFFER_LENGTH];

            map<int, int> _col2field_map;

            void construct_column_mapping(const CSV::Row &header);
            void write_header();

            void write_meta();

            inline ULONGLONG convert_to_timestamp(string &val_str);

            inline bool BinaryWriter::collect_item_to_buffer(CSV::Row row, int cur_items_num);
        };
    } // namespace datalib

} // namespace maro

#endif