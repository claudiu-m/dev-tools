// SPDX-License-Identifier:  GPL-2.0-or-later
// Copyright 2019 claudiu-m <claudiu.manoil@gmail.com>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include <unistd.h>

#define MAX_PORTS 16
uint32_t buf[65536];

static int _create_tcp_endpoint(int port)
{
	struct sockaddr_in addr;
	int sockfd;

	sockfd = socket(AF_INET, SOCK_STREAM, 0); // ipv4, tcp
	if (sockfd < 0) {
    		perror("socket creation failed");
    		return -errno;
	}

	memset(&addr, 0, sizeof(addr));
	addr.sin_family = AF_INET;
	addr.sin_port = htons(port);
	addr.sin_addr.s_addr = INADDR_ANY;

	if (bind(sockfd, (struct sockaddr *) &addr, sizeof(addr)) < 0) {
		perror("socket bind failed");
		return -errno;
	}

	return sockfd;
}

static int thread_ret;
void *client_work(void *arg){
	int port = *((int*) arg);
	int serv_fd, client_fd, n;
	struct sockaddr_in addr;
	int len, ret;

	serv_fd = _create_tcp_endpoint(port);
	if (serv_fd < 0) {
		thread_ret = serv_fd;
		return (void *)&thread_ret;
	}

	if (listen(serv_fd, 1) < 0) {
		perror("listen");
		thread_ret = -errno;
		return (void *)&thread_ret;
	}

	printf("listening on port %d\n", port);
	len = sizeof(addr);
	client_fd = accept(serv_fd, (struct sockaddr *) &addr, &len);
	if (client_fd < 0) {
		perror("accept failed");
		thread_ret = -errno;
		return (void *)&thread_ret;
	}
	printf("got new client (%d)\n", port);
	do {
		n = send(client_fd, buf, sizeof(buf), 0);
		if (n < 0)
			perror("send");
	} while (n > 0);

	shutdown(client_fd, SHUT_RD|SHUT_WR);
	close(client_fd);
	close(serv_fd);
}


int main(int argc, char **argv)
{
	pthread_t threads[MAX_PORTS];
	int port[MAX_PORTS];
	int port_base, port_range;
	int i, n, ret;
 
	if (argc != 3) {
		fprintf(stderr, "Usage: %s <port_base> <range>\n", argv[0]);
		return -EINVAL;
	}

	port_base = atoi(argv[1]);
	port_range = atoi(argv[2]);
	//printf("port_base: %d\n", port_base);
	//printf("port_range: %d\n", port_range);
	if (port_base == 0 || port_base < 0 || port_range < 0 || port_range > MAX_PORTS || port_base + port_range > 65536) {
		fprintf(stderr, "Invalid port range\n");
		return -EINVAL;
	}

	memset(buf, 0xff, sizeof(buf));

	for (i = 0; i < port_range; i++) {
		port[i] = port_base + i;
		ret = pthread_create(&threads[i], NULL, client_work, (void *)(&port[i]));
		if (ret) {
			perror("ptheread_create\n");
			return -ret;
		}
	}

	for (i = 0; i < port_range; i++) {
		ret = pthread_join(threads[i], NULL);
		if (ret) {
			perror("ptheread_create\n");
			return -ret;
		}
		printf("Thread #%d finished\n", i);
	}

	printf(">>> END\n");
	return 0;
}
