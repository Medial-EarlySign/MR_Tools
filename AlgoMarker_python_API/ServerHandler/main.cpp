#include <boost/asio.hpp>
#include <iostream>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/filesystem.hpp>
#include <boost/algorithm/string.hpp>
#include <signal.h>
#include <fstream>
#include <cmath>
#include <omp.h>

#include "utils.h"
#include "CMD_Args.h"
#include "AlgoMarker.h"

using tcp = boost::asio::ip::tcp;       // from <boost/asio.hpp>
namespace http = boost::beast::http;    // from <boost/beast/http.hpp>

#define JSON_REQ_JSON_RESP			3001
using namespace std;

class ServerGeneralSetup {
public:
	string algomarker_path;
	string lib_path;
	AlgoMarker *algomarker;
	bool silent;
	static bool CONTINUE_RUNNING;

	int init(const string &_algomarker_path, const string &_lib_path, bool _silent) {
		algomarker_path = _algomarker_path;
		lib_path = _lib_path;
		silent = _silent;
		if (lib_path.empty()) //Default
			lib_path = boost::filesystem::path(algomarker_path).parent_path().string() + "/lib/" + "libdyn_AlgoMarker.so"; 
		MLOG(false, "server setup: AlgoMarker => %s\n", algomarker_path.c_str());
		MLOG(false, "server setup: Library => %s\n", lib_path.c_str());

		load_library(lib_path.c_str());

		MLOG(false, "Create AlgoMarker interface\n");
		create_api_interface(algomarker);

		initialize_algomarker(algomarker_path.c_str(), algomarker);

		return 0;
	}

	string discovery() {
		char *jdiscovery = NULL;
		DynAM::AM_API_Discovery(algomarker, &jdiscovery);
		string res = string(jdiscovery);
		DynAM::AM_API_Dispose(jdiscovery);
		return res;
	}
	
	string debug_rep() {
		char *jresp = NULL;
		if (DynAM::so->addr_AM_API_DebugRepMemory == NULL) {
			return "{ \"error\":\"Not supported in this library\" }";
		}
		DynAM::AM_API_DebugRepMemory(algomarker, &jresp);
		string res = string(jresp);
		DynAM::AM_API_Dispose(jresp);
		return res;
	}

	string add_data(const string &json, int &rc) {
		return load_data(algomarker, json, rc);
	}

	string calculate(const string &req_json, int &rc) {
		char *jresp = NULL;
		char *jreq = (char *)(req_json.c_str());
		rc = DynAM::AM_API_CalculateByType(algomarker, JSON_REQ_JSON_RESP, jreq, &jresp);
		string res = string(jresp);
		if (jresp != NULL)
			DynAM::AM_API_Dispose(jresp);
		return res;
	}

	int clear_data() {
		return DynAM::AM_API_ClearData(algomarker);
	}

	void Dispose() {
		if (algomarker!=NULL) {
			DynAM::AM_API_ClearData(algomarker);
			DynAM::AM_API_DisposeAlgoMarker(algomarker);
			MLOG(false, "Clear AlgoMarker mem\n");
		}
		algomarker = NULL;
	}

	~ServerGeneralSetup() {
		Dispose();
	}
};

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

class http_connection : public std::enable_shared_from_this<http_connection>
{
public:

	ServerGeneralSetup *server_setup;


	//====================================================================================================================
	http_connection(tcp::socket socket, ServerGeneralSetup &_setup) : socket_(std::move(socket))
	{
		server_setup = &_setup;
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
#ifdef __linux__ 
	boost::asio::basic_waitable_timer<std::chrono::steady_clock> deadline_{
		socket_.get_executor(), std::chrono::seconds(60) };
#else
	//For Old Boost
	boost::asio::basic_waitable_timer<std::chrono::steady_clock> deadline_{
		socket_.get_executor().context(), std::chrono::seconds(60) };
#endif

	void create_get_response()
	{

		string sreq = string(request_.target());
		sreq = my_urlDecode(sreq);
		if (!server_setup->silent)
			MLOG(false,"GOT GET REQUEST ===> %s \n",sreq.c_str());

		if (request_.target() == "/")
		{
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body())
				<< "{\n"
				<< "  \"Help\": {\n"
				<< "    \"/discovery\": {\n"
				<< "      \"method\": \"GET\",\n"
				<< "      \"input\": [],\n"
				<< "      \"output\": \"returns discovery json\""
				<< "    },\n"
				<< "    \"/clear_data\": {\n"
				<< "      \"method\": \"POST\",\n"
				<< "      \"input\": [],\n"
				<< "      \"output\": \"returns code, 0 if success\""
				<< "    },\n"
				<< "    \"/add_data\": {\n"
				<< "      \"method\": \"POST\",\n"
				<< "      \"input\": [\n"
				<< "        {\n"
				<< "          \"json_data\": \"string json data with patient data\"\n"
				<< "        }\n"
				<< "      ],\n"
				<< "      \"output\": \"returns error messages if exists\"\n"
				<< "    },\n"
				<< "    \"/calculate\": {\n"
				<< "      \"method\": \"POST\",\n"
				<< "      \"input\": [\n"
				<< "        {\n"
				<< "          \"json_request\": \"string json request\"\n"
				<< "        }\n"
				<< "      ],\n"
				<< "      \"output\": \"returns response json with results\"\n"
				<< "    },\n"
				<< "    \"/config\": {\n"
				<< "      \"method\": \"GET\",\n"
				<< "      \"input\": [],\n"
				<< "      \"output\": \"returns json with server config settings: algomarker_path + library_path\""
				<< "    },\n"
				<< "    \"/alive\": {\n"
				<< "      \"method\": \"GET\",\n"
				<< "      \"input\": [],\n"
				<< "      \"output\": \"returns json with alive 1\""
				<< "    },\n"
				<< "    \"/debug_rep\": {\n"
				<< "      \"method\": \"GET\",\n"
				<< "      \"input\": [],\n"
				<< "      \"output\": \"returns json with repository data\""
				<< "    }\n"
				<< "  }\n"
				<< "}\n";
		}
		else if (request_.target() == "/alive")
		{
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body())
				<< "{\n" << "\"alive\":1\n" << "}\n";
		}
		else if (request_.target() == "/config")
		{
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body())
				<< "{\n"
				<< "\t\"algomarker_path\":\"" << server_setup->algomarker_path << "\",\n"
				<< "\t\"lib_path\":\"" << server_setup->lib_path << "\"\n"
				<< "}\n";
		}
		else if (request_.target() == "/discovery") {
			string js_res = server_setup->discovery();
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body()) << js_res;
		}
		else if (request_.target() == "/debug_rep") {
			string js_res = server_setup->debug_rep();
			response_.set(http::field::content_type, "application/json");
			boost::beast::ostream(response_.body()) << js_res;
		}
		else
		{
			response_.result(http::status::not_found);
			response_.set(http::field::content_type, "text/plain");
			boost::beast::ostream(response_.body()) << "Invalid endpoint " << request_.target();

		}
	}

	void create_post_response(const string &js_data)
		{	
			string sreq = string(request_.target());
			sreq = my_urlDecode(sreq);
			if (!server_setup->silent)
				MLOG(false,"GOT POST REQUEST ===> %s \n",sreq.c_str());
			if (request_.target() == "/add_data") {
				int rc;
				string res = server_setup->add_data(js_data, rc);
				vector<string> messages;
				stringstream ss;
				ss << "{\n" << "  \"messages\":[\n";
				if (!res.empty()) {
					boost::split(messages, res, boost::is_any_of("\n"));
					for (size_t i = 0; i<messages.size(); ++i) {
						if (i >0) 
							ss << ",\n";
						ss	<< "    \"" <<  messages[i] << "\"";
					}
				}
				 ss << "  ]\n"
				 << "\n}";
				 boost::beast::ostream(response_.body()) << ss.str();
				response_.set(http::field::content_type, "application/json");
				if (rc != AM_OK_RC) {
					response_.result(http::status::bad_request);
				}
			}
			else if (request_.target() == "/calculate") {
				int rc;
				string res = server_setup->calculate(js_data, rc);
				boost::beast::ostream(response_.body()) << res;
				response_.set(http::field::content_type, "application/json");
				if (rc != AM_OK_RC) {
					response_.result(http::status::bad_request);
				}
			}
			else if (request_.target() == "/clear_data") {
				int rc = server_setup->clear_data();
				boost::beast::ostream(response_.body()) << "{ \"return_code\":" << rc << "}";
				response_.set(http::field::content_type, "application/json");
				if (rc != AM_OK_RC) {
					response_.result(http::status::bad_request);
				}
			}
			else
			{
				response_.result(http::status::not_found);
				response_.set(http::field::content_type, "text/plain");
				boost::beast::ostream(response_.body()) << "Invalid endpoint " << request_.target();

			}

		}
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
			if (!server_setup->silent)
				MLOG(false, "BUG in boost::http - changed to post\n");
		}

		switch (method_r)
		{
		case http::verb::get:
			//MLOG(false,"Got a GET request\n");
			response_.result(http::status::ok);
			response_.set(http::field::server, "BoostBeast");
			create_get_response();
			break;

		case http::verb::post:
		{
			//MLOG(false, "Got a POST request\n");
			response_.result(http::status::ok);
			response_.set(http::field::server, "BoostBeast");

			string s = boost::beast::buffers_to_string(request_.body().data());
			//MLOG("REQUEST BODY: %s\n", s.c_str());
			create_post_response(s);
		}
		break;

		default:
			if (!server_setup->silent)
				MLOG(false, "Got a invalid request-method\n");
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
	// Construct a response message based on the program state.
	//====================================================================================================================
	

	//====================================================================================================================
	// Asynchronously transmit the response message.
	//====================================================================================================================
	void write_response()
	{
		auto self = shared_from_this();

		response_.set(http::field::content_length, string_view(to_string(response_.body().size())));
		response_.prepare_payload();

		http::async_write(
			socket_,
			response_,
			[self](boost::beast::error_code ec, std::size_t)
		{
			self->socket_.shutdown(tcp::socket::shutdown_send, ec);
			self->deadline_.cancel();
		});
		
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


void http_server(tcp::acceptor& acceptor, tcp::socket& socket, ServerGeneralSetup &_setup)
{
	acceptor.async_accept(socket,
		[&](boost::beast::error_code ec)
	{
		if (!ec)
			std::make_shared<http_connection>(std::move(socket), _setup)->start();
		if (ServerGeneralSetup::CONTINUE_RUNNING)
			http_server(acceptor, socket, _setup);
	});
}

ServerGeneralSetup *server_p = NULL;
bool ServerGeneralSetup::CONTINUE_RUNNING = true;

void exit_handler(int s) {
	printf("Caught signal %d - CTRL+C\n", s);
	//call finish test_am
	ServerGeneralSetup::CONTINUE_RUNNING = false; 
	if (server_p != NULL) {
		//add Lock
		server_p->Dispose();
		server_p = NULL;
	}
	printf("Done, exit\n");
	exit(1);
}

int main(int argc, char* argv[])
{
	signal(SIGINT, exit_handler);
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	// Check if we are inside docker and have limits:
	string cpu_limit_path = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us";
	ifstream cpu_f(cpu_limit_path);
	if (cpu_f.good()) {
		string limit_txt;
		getline(cpu_f, limit_txt);
		cpu_f.close();
		if (!limit_txt.empty()) {
			long numeric_limit = stol(limit_txt);
			if (numeric_limit > 0) {
				// Has Real limit:
				
				int cpu_count_limit = (int)round(numeric_limit / 100000.0+0.5);
				if (cpu_count_limit <= 0)
					cpu_count_limit = 1;
				// Set limit to cpu_count_limit
				printf("Found Real CPU limit - %ld - setting limit to %d\n", numeric_limit, cpu_count_limit);
				omp_set_num_threads(cpu_count_limit);
			}
		}
	}

	// Reading run Parameters
	ServerGeneralSetup _setup;

	_setup.init(args.algomarker_path, args.library_path, args.no_prints);
	server_p = &_setup;
	int threads = args.num_of_threads;
	if (threads <= 0) {
		threads = omp_get_max_threads();
	}
	MLOG(false, "Start Server with %d threads(%d input)...\n", threads, args.num_of_threads);
	MLOG(false, "address => %s:%d\n", args.address.c_str(), (int)args.port);
	
	try
	{
		auto const address = boost::asio::ip::make_address(args.address);

		boost::asio::io_context ioc{ threads };

		tcp::acceptor acceptor{ ioc,{ address, args.port } };
		tcp::socket socket{ ioc };
		http_server(acceptor, socket, _setup);

		ioc.run();
	}
	catch (exception const& e)
	{
		cerr << "Error: " << e.what() << endl;
		return EXIT_FAILURE;
	}
}
