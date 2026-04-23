#!/usr/bin/env ruby
require 'webrick'
port = (ARGV[0] || 8080).to_i
root = File.dirname(File.expand_path(__FILE__))
server = WEBrick::HTTPServer.new(Port: port, DocumentRoot: root, Logger: WEBrick::Log.new('/dev/null'), AccessLog: [])
trap('INT') { server.shutdown }
server.start
