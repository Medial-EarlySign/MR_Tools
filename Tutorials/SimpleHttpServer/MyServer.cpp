#define _CRT_SECURE_NO_WARNINGS

//
// Copyright (c) 2017 Christopher M. Kohlhoff (chris at kohlhoff dot com)
//
// Distributed under the Boost Software License, Version 1.0. (See accompanying
// file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
//
// Official repository: https://github.com/boostorg/beast
//

//------------------------------------------------------------------------------
//
// Example: HTTP server, small
//
//------------------------------------------------------------------------------

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/version.hpp>
#include <boost/asio.hpp>
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <memory>
#include <string>
#include <MedIO/MedIO/MedIO.h>
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedPlotly/MedPlotly/MedPlotly.h>
#include <Logger/Logger/Logger.h>
#include <boost/algorithm/string/predicate.hpp>
#include <utility>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>

namespace pt = boost::property_tree;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

using namespace std;
namespace po = boost::program_options;

namespace ip = boost::asio::ip;         // from <boost/asio.hpp>
using tcp = boost::asio::ip::tcp;       // from <boost/asio.hpp>
namespace http = boost::beast::http;    // from <boost/beast/http.hpp>

//========================================================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("plotly_config", po::value<string>()->default_value("//nas1/UsersData/avi/MR/Libs/Internal/MedPlotly/MedPlotly/BasicConfig.txt"), "config file for medplotly")
			("server_dir", po::value<string>()->default_value("//nas1/UsersData/avi/MR/Libs/Internal/MedPlotly/JavaScript"), "directory for server files")
			("address", po::value<string>()->default_value("192.168.1.224"), "ip of server")
			("port", po::value<string>()->default_value("8192"), "port of server")
			("index_page", po::value<string>()->default_value("form.html"))
			;


		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i = 0; i < argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	return 0;
}

//====================================================================================================================
string my_urlDecode(string &SRC)
{
	string ret;
	char ch;
	int i, ii;
	for (i = 0; i < SRC.length(); i++) {
		if (int(SRC[i]) == 37) {
			sscanf(SRC.substr(i + 1, 2).c_str(), "%x", &ii);
			ch = static_cast<char>(ii);
			ret += ch;
			i = i + 2;
		}
		else {
			ret += SRC[i];
		}
	}
	return (ret);
}

//====================================================================================================================
namespace my_program_state
{

	//====================================================================================================================
	std::size_t	request_count(bool only_query = true)
	{
		static std::size_t count = 0;
		if (!only_query)
			++count;
		return count;
	}

	//====================================================================================================================
	std::time_t	now()
	{
		return std::time(0);
	}
}

//====================================================================================================================
class ServerGeneralSetup {
public:
	string rep_fname;
	MedPidRepository *rep = NULL;
	MedPatientPlotlyDate *mplot = (MedPatientPlotlyDate *)NULL;

	string files_directory; // for .js , .css , .html files
	string plotly_config_file;
	string deafult_index_page;

	int init(string _rep_fname, string _files_directory, string _plotly_config_file, const string &index_page) {

		rep_fname = _rep_fname;
		files_directory = _files_directory;
		plotly_config_file = _plotly_config_file;
		deafult_index_page = index_page;

		if (rep != NULL) delete rep;
		if (mplot != NULL) delete mplot;

		rep = new MedPidRepository;
		mplot = new MedPatientPlotlyDate;

		if (mplot->read_config(plotly_config_file) < 0) return -1;
		if (rep->init(rep_fname) < 0) return -1;
		if (mplot->init_rep_processors(*rep, rep_fname) < 0) return -1;

		MLOG("server setup: rep => %s\n", rep_fname.c_str());
		MLOG("server setup: plotly_config => %s\n", plotly_config_file.c_str());
		MLOG("server setup: server_dir => %s\n", files_directory.c_str());

		return 0;
	}

	int get_pid(int pid, PidDataRec &res) {
		if (mplot->params.model_rep_processors.rep_processors.empty()) {
			res.use_dynamic = false;
			if (rep->get_pid_rec(pid, res.rec_static) < 0)
				return -1;
		}
		else {
			res.use_dynamic = true;
			//has rep processors:

			vector<int> all_sigs = rep->sigs.signals_ids;
			if (mplot->params.load_dynamically) {
				const vector<string> &all_sigs_names = mplot->params.all_need_sigs;
				vector<int> all_pids = { pid };
				if (rep->read_all(rep_fname, all_pids, mplot->params.phisical_read_sigs) < 0) {
					MERR("Flow: get_model_preds: could not read repository %s\n", rep_fname.c_str());
					return -1;
				}
				vector<string> temp;
				medial::repository::prepare_repository(*rep, all_sigs_names, temp, &mplot->params.model_rep_processors.rep_processors); //prepare again after reading
				//populate all_sigs:
				all_sigs.clear(); all_sigs.resize(all_sigs_names.size());
				for (size_t i = 0; i < all_sigs_names.size(); ++i)
				{
					all_sigs[i] = rep->sigs.sid(all_sigs_names[i]);
					if (all_sigs[i] < 0)
						MTHROW_AND_ERR("Error can't find signal %s\n", all_sigs_names[i].c_str());
				}
			}

			if (res.rec_dynamic.init_from_rep(rep, pid, all_sigs, 1) < 0)
				return -1;
			vector<int> time_pnt = { INT_MAX };
			vector<vector<float>> attr;
			for (RepProcessor *rep_proc : mplot->params.model_rep_processors.rep_processors)
				rep_proc->apply(res.rec_dynamic, time_pnt, attr);
		}

		return 0;
	}
};

//====================================================================================================================
class http_connection : public std::enable_shared_from_this<http_connection>
{
public:

	ServerGeneralSetup server_setup;


	//====================================================================================================================
	http_connection(tcp::socket socket, ServerGeneralSetup &_setup) : socket_(std::move(socket))
	{
		server_setup = _setup;
	}

	//====================================================================================================================
	// Initiate the asynchronous operations associated with the connection.
	//====================================================================================================================
	void start()
	{
		read_request();
		check_deadline();
	}

private:
	// The socket for the currently connected client.
	tcp::socket socket_;

	// The buffer for performing reads.
	boost::beast::flat_buffer buffer_{ 8192 };

	// The request message.
	http::request<http::dynamic_body> request_;

	// The response message.
	http::response<http::dynamic_body> response_;

	// The timer for putting a deadline on connection processing.
	boost::asio::basic_waitable_timer<std::chrono::steady_clock> deadline_{
		socket_.get_executor(), std::chrono::seconds(60) };


	//====================================================================================================================
	// Asynchronously receive a complete request message.
	//====================================================================================================================
	void read_request()
	{
		auto self = shared_from_this();

		http::async_read(
			socket_,
			buffer_,
			request_,
			[self](boost::beast::error_code ec,
				std::size_t bytes_transferred)
		{
			boost::ignore_unused(bytes_transferred);
			if (!ec)
				self->process_request();
		});
	}

	//====================================================================================================================
	// Determine what needs to be done with the request message.
	//====================================================================================================================
	void process_request()
	{
		response_.clear();
		response_.version(request_.version());
		response_.keep_alive(request_.keep_alive());

		http::verb method_r = request_.method();
		if (request_.method() == http::verb::unknown && request_.method_string() == "POST") {
			method_r = http::verb::post;
			MLOG("BUG in boost::http - changed to post\n");
		}

		switch (method_r)
		{
		case http::verb::get:
			MLOG("Got a GET request\n");
			response_.result(http::status::ok);
			response_.set(http::field::server, "Beast");
			create_response();
			break;

		case http::verb::post:
		{
			MLOG("Got a POST request\n");
			response_.result(http::status::ok);
			response_.set(http::field::server, "Beast");

			string s = boost::beast::buffers_to_string(request_.body().data());
			MLOG("REQUEST BODY: %s\n", s.c_str());
			create_pid_page_request(s);
		}
		break;

		default:
			MLOG("Got a default request\n");
			// We return responses indicating an error if
			// we do not recognize the request method.
			response_.result(http::status::bad_request);
			response_.set(http::field::content_type, "text/plain");
			boost::beast::ostream(response_.body())
				<< "Invalid request-method '"
				<< string(request_.method_string())
				<< "'";
			break;
		}

		write_response();
	}

	//====================================================================================================================
	// gets a json with parameters and creates an html page as a response with the matching patient viewer
	//====================================================================================================================
	void create_pid_page_request(string &in_json)
	{
		stringstream s;
		s << in_json;
		pt::ptree tree;

		// first we need to parse json and get our basic params
		pt::read_json(s, tree);

		int pid = tree.get<int>("pid", 0);
		int date = tree.get<int>("date", 0);
		int from_date = tree.get<int>("from_date", 0);
		int to_date = tree.get<int>("to_date", 0);

		vector<string> view;
		for (auto sp : tree.get_child("panels"))
			view.push_back(sp.second.get_value<string>());

		string sigs_s = tree.get<string>("signals", "");

		if (view.size() == 0) view = server_setup.mplot->params.views;
		vector<string> fields;
		boost::split(fields, sigs_s, boost::is_any_of(" ,\n\t\r;"));
		for (auto f : fields)
			if (f != "")
				view.push_back(f);

		string date_desc = tree.get<string>("desc", "");

		MLOG("Got: pid %d , date %d , desc %s\n", pid, date, date_desc.c_str());
		MLOG("view is : ");
		for (auto v : view) MLOG(" %s ,", v.c_str());
		MLOG("\n");

		vector<ChartTimeSign> cts;
		if (date > 0) {
			cts.push_back(ChartTimeSign(date, date_desc, "'black'"));
		}

		PidDataRec rec;
		string shtml;
		LocalViewsParams lvp(pid, from_date, to_date);

		if (server_setup.get_pid(pid, rec) >= 0)
			server_setup.mplot->get_rec_html(shtml, lvp, rec, "server", cts, view);
		else
			shtml = "<html><h1>Bad Request for pid : no such pid in repository</h1></html>\n";

		MLOG("Got shtml of length %d\n", shtml.size());

		response_.set(http::field::content_type, "text/html");
		boost::beast::ostream(response_.body()) << shtml;
		MLOG("Writing shtml file\n");
		my_program_state::request_count(false);
		//write_string("last_shtml.html", shtml);
	}

	//====================================================================================================================
	// Construct a response message based on the program state.
	//====================================================================================================================
	void create_response()
	{

		string sreq = string(request_.target());
		sreq = my_urlDecode(sreq);
		if (sreq == "/") { //look for default: index.html, index.htm, form.html (in that order)
			if (file_exists(server_setup.files_directory + "/" + server_setup.deafult_index_page))
				sreq = "/" + server_setup.deafult_index_page;
			else if (file_exists(server_setup.files_directory + "/index.html"))
				sreq = "/index.html";
			else if (file_exists(server_setup.files_directory + "/index.htm"))
				sreq = "/index.htm";
			else if (file_exists(server_setup.files_directory + "/form.html"))
				sreq = "/form.html";
		}

		MLOG("GOT REQUEST ===> %s \n", sreq.c_str());

		if (request_.target() == "/count")
		{
			response_.set(http::field::content_type, "text/html");
			boost::beast::ostream(response_.body())
				<< "<html>\n"
				<< "<head><title>Request count</title></head>\n"
				<< "<body>\n"
				<< "<h1>Request count</h1>\n"
				<< "<p>There have been "
				<< my_program_state::request_count()
				<< " requests so far.</p>\n"
				<< "</body>\n"
				<< "</html>\n";
		}
		else if (request_.target() == "/time")
		{
			response_.set(http::field::content_type, "text/html");
			boost::beast::ostream(response_.body())
				<< "<html>\n"
				<< "<head><title>Current time</title></head>\n"
				<< "<body>\n"
				<< "<h1>Current time</h1>\n"
				<< "<p>The current time is "
				<< my_program_state::now()
				<< " seconds since the epoch.</p>\n"
				<< "</body>\n"
				<< "</html>\n";
		}
		else if (request_.target() == "/config")
		{
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body())
				<< "{\n"
				<< "\t\"rep_fname\":\"" << server_setup.rep_fname << "\",\n"
				<< "\t\"files_directory\":\"" << server_setup.files_directory << "\",\n"
				<< "\t\"plotly_config_file\":\"" << server_setup.plotly_config_file << "\",\n"
				<< "\t\"deafult_index_page\":\"" << server_setup.deafult_index_page << "\"\n"
				<< "}\n";
		}
		else if (request_.target().substr(0, 4) == "/pid") {
			string shtml;

			vector<string> f;
			boost::split(f, sreq, boost::is_any_of(","));
			if (f.size() >= 4) {
				int pid = stoi(f[1]);
				int time = stoi(f[2]);
				string desc = f[3];
				string panels_order = "";
				vector<string> views_list = server_setup.mplot->params.views;
				if (f.size() > 4) {
					panels_order = f[4];
					views_list.clear();
					//split to view order by sep of &:
					boost::split(views_list, panels_order, boost::is_any_of("&"));
				}


				PidDataRec rec;
				LocalViewsParams lvp(pid, 0, 0);

				server_setup.get_pid(pid, rec);
				server_setup.mplot->get_rec_html(shtml, lvp, rec, "server", { ChartTimeSign(time, desc, "'black'") },
					views_list);
			}
			else {
				shtml = "<html><h1>Bad Request for pid,time</h1></html>\n";
			}

			response_.set(http::field::content_type, "text/html");

			boost::beast::ostream(response_.body()) << shtml;
			my_program_state::request_count(false);
		}
		else if (boost::algorithm::ends_with(sreq, ".js") ||
			boost::algorithm::ends_with(sreq, ".html") ||
			boost::algorithm::ends_with(sreq, ".css")) {

			MLOG("File Request\n");

			if (boost::algorithm::ends_with(sreq, ".js")) response_.set(http::field::content_type, "application/javascript");
			if (boost::algorithm::ends_with(sreq, ".html")) response_.set(http::field::content_type, "text/html");
			if (boost::algorithm::ends_with(sreq, ".css")) response_.set(http::field::content_type, "text/css");

			vector<char> fstr;
			string str;
			string file_to_read = server_setup.files_directory + sreq;

			MLOG("Returning file %s\n", file_to_read.c_str());

			read_vector<char>(file_to_read, fstr);
			fstr.push_back(0);
			str = string(&fstr[0]);

			boost::beast::ostream(response_.body()) << str; // << "\r\n";

			//boost::beast::ostream(response_.body()) << "WALLA\r\n";
			cout << "WALLA !!!! str len " << str.length() << " vs " << response_.body().size() << endl;
		}
		else
		{
			response_.result(http::status::not_found);
			response_.set(http::field::content_type, "text/plain");
			boost::beast::ostream(response_.body()) << "File not found\r\n";

		}
	}

	//====================================================================================================================
	// Asynchronously transmit the response message.
	//====================================================================================================================
	void write_response()
	{
		auto self = shared_from_this();

		response_.set(http::field::content_length, string_view(to_string(response_.body().size())));
		response_.prepare_payload();

		if (response_.need_eof())
			MLOG("=====> NEED EOF !\n");
		else
			MLOG("=====> EOF not needed!\n");

		if (0) { //request_.method() == http::verb::get) {

			//http::write(_response);

		}
		else {

			http::async_write(
				socket_,
				response_,
				[self](boost::beast::error_code ec, std::size_t)
			{
				self->socket_.shutdown(tcp::socket::shutdown_send, ec);
				self->deadline_.cancel();
			});
		}
	}

	//====================================================================================================================
	// Check whether we have spent enough time on this connection.
	//====================================================================================================================
	void check_deadline()
	{
		auto self = shared_from_this();

		deadline_.async_wait(
			[self](boost::beast::error_code ec)
		{
			if (!ec)
			{
				// Close socket to cancel any outstanding operation.
				self->socket_.close(ec);
			}
		});
	}
};

//====================================================================================================================
// "Loop" forever accepting new connections.
//====================================================================================================================
void http_server(tcp::acceptor& acceptor, tcp::socket& socket, ServerGeneralSetup &_setup)
{
	acceptor.async_accept(socket,
		[&](boost::beast::error_code ec)
	{
		if (!ec)
			std::make_shared<http_connection>(std::move(socket), _setup)->start();
		http_server(acceptor, socket, _setup);
	});
}

//====================================================================================================================
// SERVER MAIN
//====================================================================================================================
int main(int argc, char* argv[])
{
	int rc = 0;
	po::variables_map vm;

	// Reading run Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm);
	assert(rc >= 0);

	ServerGeneralSetup _setup;

	_setup.init(vm["rep"].as<string>(), vm["server_dir"].as<string>(), vm["plotly_config"].as<string>(), vm["index_page"].as<string>());

	try
	{
		auto const address = boost::asio::ip::make_address(vm["address"].as<string>().c_str());
		unsigned short port = static_cast<unsigned short>(stoi(vm["port"].as<string>()));

		boost::asio::io_context ioc{ 1 };

		tcp::acceptor acceptor{ ioc,{ address, port } };
		tcp::socket socket{ ioc };
		http_server(acceptor, socket, _setup);

		ioc.run();
	}
	catch (std::exception const& e)
	{
		std::cerr << "Error: " << e.what() << std::endl;
		return EXIT_FAILURE;
	}
}
